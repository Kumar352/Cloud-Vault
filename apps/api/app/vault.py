"""Authenticated file, version, sharing, audit, retrieval, and analytics API."""

from __future__ import annotations

import json
import re
import sqlite3
import uuid
from urllib.parse import quote, unquote

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app import anomaly, rag
from app.auth import DEMO_USERS_BY_EMAIL, Principal, current_principal
from app.database import audit, connect, utc_now
from app.storage import delete as delete_object, get, put


router = APIRouter(tags=["vault"])
MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_TENANT_STORAGE_BYTES = 50 * 1024 * 1024
MAX_FILES_PER_OWNER = 100
MAX_VERSIONS_PER_FILE = 20
MAX_QUEUED_SCANS_PER_TENANT = 25
MAX_ASSISTANT_REQUESTS_PER_DAY = 50
FILENAME_LIMIT = 120
SAFE_NAME = re.compile(r"[^\w. ()@+-]", re.UNICODE)


class ShareRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    permission: str = Field(pattern="^(read|write)$")


class QuestionRequest(BaseModel):
    question: str = Field(min_length=2, max_length=1000)


def _file(file_id: str, principal: Principal, *, permission: str = "read") -> sqlite3.Row:
    with connect() as db:
        file = db.execute(
            "SELECT * FROM files WHERE id=? AND tenant_id=?",
            (file_id, principal.tenant_id),
        ).fetchone()
        share = None if file is None or file["owner_id"] == principal.user_id else db.execute(
            "SELECT permission FROM shares WHERE file_id=? AND user_id=?",
            (file_id, principal.user_id),
        ).fetchone()
    if file is None:
        raise HTTPException(status_code=404, detail="File not found")
    if file["owner_id"] == principal.user_id:
        return file
    if share is None or (permission == "write" and share["permission"] != "write"):
        with connect() as db:
            audit(db, principal.tenant_id, principal.user_id, "access_denied", file_id, {"permission": permission})
        raise HTTPException(status_code=404, detail="File not found")
    return file


def _owner(file_id: str, principal: Principal) -> sqlite3.Row:
    file = _file(file_id, principal)
    if file["owner_id"] != principal.user_id:
        raise HTTPException(status_code=404, detail="File not found")
    return file


def _latest(db: sqlite3.Connection, file_id: str) -> sqlite3.Row | None:
    return db.execute(
        "SELECT * FROM file_versions WHERE file_id=? ORDER BY version DESC LIMIT 1", (file_id,)
    ).fetchone()


def _version_row(version_id: str, principal: Principal) -> tuple[sqlite3.Row, sqlite3.Row]:
    with connect() as db:
        version = db.execute("SELECT * FROM file_versions WHERE id=?", (version_id,)).fetchone()
    if version is None:
        raise HTTPException(status_code=404, detail="File version not found")
    file = _file(version["file_id"], principal)
    return file, version


@router.get("/files")
def list_files(principal: Principal = Depends(current_principal)) -> list[dict[str, object]]:
    with connect() as db:
        rows = db.execute(
            """SELECT f.id,f.name,f.owner_id,f.created_at,
                      v.id AS version_id,v.version,v.size_bytes,v.scan_state,v.created_at AS version_created,
                      CASE WHEN f.owner_id=? THEN 'owner' ELSE s.permission END AS access
               FROM files f
               JOIN file_versions v ON v.id=(SELECT id FROM file_versions WHERE file_id=f.id ORDER BY version DESC LIMIT 1)
               LEFT JOIN shares s ON s.file_id=f.id AND s.user_id=?
               WHERE f.tenant_id=? AND (f.owner_id=? OR s.user_id IS NOT NULL)
               ORDER BY v.created_at DESC""",
            (principal.user_id, principal.user_id, principal.tenant_id, principal.user_id),
        ).fetchall()
        return [dict(row) for row in rows]


async def _read_limited(request: Request) -> bytes:
    length = request.headers.get("content-length")
    if length and (not length.isdigit() or int(length) > MAX_UPLOAD_BYTES):
        raise HTTPException(status_code=413, detail="Maximum upload size is 10 MiB")
    data = bytearray()
    async for chunk in request.stream():
        data.extend(chunk)
        if len(data) > MAX_UPLOAD_BYTES:
            raise HTTPException(status_code=413, detail="Maximum upload size is 10 MiB")
    if not data:
        raise HTTPException(status_code=400, detail="Upload is empty")
    return bytes(data)


def _clean_filename(value: str | None) -> str:
    value = unquote(value) if value else value
    if not value or len(value) > FILENAME_LIMIT or any(character in value for character in "\r\n\x00/\\"):
        raise HTTPException(status_code=400, detail="A simple filename up to 120 characters is required")
    value = SAFE_NAME.sub("_", value).strip(" .")
    if not value or value in {".", ".."}:
        raise HTTPException(status_code=400, detail="Filename is invalid")
    return value


def _save_version(file_id: str, filename: str, data: bytes, principal: Principal, content_type: str) -> dict[str, object]:
    object_key = str(uuid.uuid4())
    file_id_version = object_key
    import hashlib
    digest = hashlib.sha256(data).hexdigest()
    with connect() as db:
        record = db.execute("SELECT id,owner_id FROM files WHERE id=? AND tenant_id=?", (file_id, principal.tenant_id)).fetchone()
        if record is None:
            raise HTTPException(status_code=404, detail="File not found")
        if record["owner_id"] != principal.user_id:
            share = db.execute("SELECT permission FROM shares WHERE file_id=? AND user_id=?", (file_id, principal.user_id)).fetchone()
            if share is None or share["permission"] != "write":
                raise HTTPException(status_code=404, detail="File not found")
        version = db.execute("SELECT COALESCE(MAX(version),0)+1 FROM file_versions WHERE file_id=?", (file_id,)).fetchone()[0]
        if version > MAX_VERSIONS_PER_FILE:
            raise HTTPException(status_code=429, detail="This file has reached the 20-version local limit")
        stored_bytes = db.execute(
            "SELECT COALESCE(SUM(v.size_bytes),0) FROM file_versions v JOIN files f ON f.id=v.file_id WHERE f.tenant_id=?",
            (principal.tenant_id,),
        ).fetchone()[0]
        if stored_bytes + len(data) > MAX_TENANT_STORAGE_BYTES:
            raise HTTPException(status_code=413, detail="The local vault has reached its 50 MiB total storage limit")
        queued = db.execute(
            "SELECT COUNT(*) FROM file_versions v JOIN files f ON f.id=v.file_id WHERE f.tenant_id=? AND v.scan_state IN ('queued','scanning')",
            (principal.tenant_id,),
        ).fetchone()[0]
        if queued >= MAX_QUEUED_SCANS_PER_TENANT:
            raise HTTPException(status_code=429, detail="The local scan queue is full; wait for scans to finish")
        put(object_key, data, clean=False)
        now = utc_now()
        db.execute(
            "INSERT INTO file_versions(id,file_id,version,object_key,sha256,size_bytes,media_type,scan_state,created_at) VALUES(?,?,?,?,?,?,?,?,?)",
            (file_id_version, file_id, version, object_key, digest, len(data), content_type[:120], "queued", now),
        )
        audit(db, principal.tenant_id, principal.user_id, "file.upload_queued", file_id,
              {"version": version, "size_bytes": len(data), "sha256": digest, "filename": filename})
    return {"file_id": file_id, "version_id": file_id_version, "version": version, "sha256": digest,
            "size_bytes": len(data), "scan_state": "queued", "message": "Stored encrypted in quarantine; scan worker must approve it before download."}


@router.post("/files", status_code=status.HTTP_202_ACCEPTED)
async def upload_file(request: Request, principal: Principal = Depends(current_principal)) -> dict[str, object]:
    filename = _clean_filename(request.headers.get("x-file-name"))
    data = await _read_limited(request)
    with connect() as db:
        existing = db.execute(
            "SELECT id FROM files WHERE owner_id=? AND name=? COLLATE NOCASE",
            (principal.user_id, filename),
        ).fetchone()
        file_id = existing["id"] if existing else str(uuid.uuid4())
        if not existing:
            count = db.execute("SELECT COUNT(*) FROM files WHERE tenant_id=? AND owner_id=?", (principal.tenant_id, principal.user_id)).fetchone()[0]
            if count >= MAX_FILES_PER_OWNER:
                raise HTTPException(status_code=429, detail="The local account has reached its 100-file limit")
            db.execute("INSERT INTO files(id,tenant_id,owner_id,name,created_at) VALUES(?,?,?,?,?)",
                       (file_id, principal.tenant_id, principal.user_id, filename, utc_now()))
    return _save_version(file_id, filename, data, principal, request.headers.get("content-type", "application/octet-stream"))


@router.post("/files/{file_id}/versions", status_code=status.HTTP_202_ACCEPTED)
async def upload_version(file_id: str, request: Request, principal: Principal = Depends(current_principal)) -> dict[str, object]:
    file = _file(file_id, principal, permission="write")
    data = await _read_limited(request)
    return _save_version(file_id, file["name"], data, principal,
                         request.headers.get("content-type", "application/octet-stream"))


@router.get("/files/{file_id}/versions")
def list_versions(file_id: str, principal: Principal = Depends(current_principal)) -> list[dict[str, object]]:
    _file(file_id, principal)
    with connect() as db:
        rows = db.execute(
            "SELECT id,version,size_bytes,sha256,scan_state,scan_detail,created_at FROM file_versions WHERE file_id=? ORDER BY version DESC",
            (file_id,),
        ).fetchall()
        return [dict(row) for row in rows]


@router.delete("/files/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_file(file_id: str, principal: Principal = Depends(current_principal)) -> Response:
    file = _owner(file_id, principal)
    with connect() as db:
        versions = db.execute("SELECT object_key FROM file_versions WHERE file_id=?", (file_id,)).fetchall()
    try:
        for version in versions:
            delete_object(version["object_key"])
    except OSError as error:
        raise HTTPException(status_code=503, detail="The local object could not be removed safely") from error
    with connect() as db:
        db.execute("DELETE FROM rag_chunks WHERE file_id=?", (file_id,))
        db.execute("DELETE FROM shares WHERE file_id=?", (file_id,))
        db.execute("DELETE FROM file_versions WHERE file_id=?", (file_id,))
        db.execute("DELETE FROM files WHERE id=?", (file_id,))
        audit(db, principal.tenant_id, principal.user_id, "file.deleted", file_id,
              {"filename": file["name"], "versions_removed": len(versions)})
    return Response(status_code=204)


@router.post("/versions/{version_id}/retry-scan", status_code=status.HTTP_202_ACCEPTED)
def retry_scan(version_id: str, principal: Principal = Depends(current_principal)) -> dict[str, str]:
    file, _ = _version_row(version_id, principal)
    _owner(file["id"], principal)
    with connect() as db:
        cursor = db.execute(
            "UPDATE file_versions SET scan_state='queued',scan_detail=NULL WHERE id=? AND scan_state='error'",
            (version_id,),
        )
        if not cursor.rowcount:
            raise HTTPException(status_code=409, detail="Only a failed scan can be retried")
        audit(db, principal.tenant_id, principal.user_id, "file.scan_retry_queued", file["id"])
    return {"version_id": version_id, "scan_state": "queued"}


@router.get("/files/{file_id}/download")
def download_file(file_id: str, principal: Principal = Depends(current_principal)):
    _file(file_id, principal)
    with connect() as db:
        version = _latest(db, file_id)
        if version is None or version["scan_state"] != "clean":
            raise HTTPException(status_code=409, detail="Only the latest clean file version can be downloaded")
        data = get(version["object_key"], clean=True)
        audit(db, principal.tenant_id, principal.user_id, "file.download", file_id,
              {"version": version["version"], "size_bytes": version["size_bytes"]})
        filename = db.execute("SELECT name FROM files WHERE id=?", (file_id,)).fetchone()["name"]
    encoded = quote(filename, safe="")
    return StreamingResponse(iter([data]), media_type="application/octet-stream",
                             headers={"Content-Disposition": f"attachment; filename*=utf-8''{encoded}"})


@router.post("/files/{file_id}/shares")
def grant_share(file_id: str, body: ShareRequest, principal: Principal = Depends(current_principal)) -> dict[str, object]:
    _owner(file_id, principal)
    target = DEMO_USERS_BY_EMAIL.get(body.email.casefold())
    if target is None or target[1] != principal.tenant_id or target[0] == principal.user_id:
        raise HTTPException(status_code=400, detail="Choose another enabled synthetic account in your tenant")
    with connect() as db:
        db.execute(
            "INSERT INTO shares(file_id,user_id,permission,added_by,created_at) VALUES(?,?,?,?,?) "
            "ON CONFLICT(file_id,user_id) DO UPDATE SET permission=excluded.permission,added_by=excluded.added_by,created_at=excluded.created_at",
            (file_id, target[0], body.permission, principal.user_id, utc_now()),
        )
        audit(db, principal.tenant_id, principal.user_id, "share.granted", file_id,
              {"target_user": target[0], "permission": body.permission})
    return {"file_id": file_id, "user_id": target[0], "permission": body.permission}


@router.get("/files/{file_id}/shares")
def list_shares(file_id: str, principal: Principal = Depends(current_principal)) -> list[dict[str, object]]:
    _owner(file_id, principal)
    with connect() as db:
        return [dict(row) for row in db.execute(
            "SELECT u.id AS user_id,u.email,s.permission,s.created_at FROM shares s JOIN users u ON u.id=s.user_id WHERE s.file_id=? ORDER BY u.email",
            (file_id,),
        ).fetchall()]


@router.delete("/files/{file_id}/shares/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_share(file_id: str, user_id: str, principal: Principal = Depends(current_principal)) -> Response:
    _owner(file_id, principal)
    with connect() as db:
        cursor = db.execute("DELETE FROM shares WHERE file_id=? AND user_id=?", (file_id, user_id))
        if cursor.rowcount:
            audit(db, principal.tenant_id, principal.user_id, "share.revoked", file_id, {"target_user": user_id})
    return Response(status_code=204)


@router.get("/audit")
def list_audit(limit: int = 100, principal: Principal = Depends(current_principal)) -> list[dict[str, object]]:
    limit = min(max(limit, 1), 200)
    with connect() as db:
        rows = db.execute(
            "SELECT id,user_id,action,resource_id,details_json,created_at FROM audit_events WHERE tenant_id=? AND user_id=? ORDER BY id DESC LIMIT ?",
            (principal.tenant_id, principal.user_id, limit),
        ).fetchall()
    return [{**dict(row), "details": json.loads(row["details_json"])} for row in rows]


@router.post("/assistant/ask")
def ask_assistant(body: QuestionRequest, principal: Principal = Depends(current_principal)) -> dict[str, object]:
    with connect() as db:
        today = utc_now()[:10]
        db.execute(
            "INSERT INTO assistant_usage(user_id,usage_date,request_count) VALUES(?,?,1) "
            "ON CONFLICT(user_id,usage_date) DO UPDATE SET request_count=request_count+1",
            (principal.user_id, today),
        )
        count = db.execute("SELECT request_count FROM assistant_usage WHERE user_id=? AND usage_date=?", (principal.user_id, today)).fetchone()[0]
        if count > MAX_ASSISTANT_REQUESTS_PER_DAY:
            raise HTTPException(status_code=429, detail="The local assistant limit is 50 questions per day")
    response = rag.answer(body.question, principal.user_id, principal.tenant_id)
    with connect() as db:
        audit(db, principal.tenant_id, principal.user_id, "assistant.query", details={"mode": response["mode"], "citation_count": len(response["citations"])})
    return response


@router.get("/analytics/anomaly-evaluation")
def anomaly_evaluation(principal: Principal = Depends(current_principal)) -> dict[str, object]:
    with connect() as db:
        audit(db, principal.tenant_id, principal.user_id, "analytics.anomaly_evaluation")
    return anomaly.synthetic_evaluation()


@router.post("/analytics/analyze")
def analyze_activity(principal: Principal = Depends(current_principal)) -> dict[str, object]:
    import random
    rng = random.Random(19)
    baseline = [
        [max(0, rng.gauss(4, 1.5)), max(0, rng.gauss(40_000, 18_000)), max(0, rng.gauss(0.1, 0.35)), max(1, rng.gauss(3, 1.2))]
        for _ in range(128)
    ]
    model = anomaly.IsolationForest().fit(baseline)
    with connect() as db:
        events = db.execute(
            "SELECT action,resource_id,details_json,created_at FROM audit_events WHERE tenant_id=? AND user_id=? AND created_at>=datetime('now','-1 day')",
            (principal.tenant_id, principal.user_id),
        ).fetchall()
    hourly: dict[str, list[object]] = {}
    for event in events:
        bucket = str(event["created_at"])[:13]
        features = hourly.setdefault(bucket, [0.0, 0.0, 0.0, set()])
        action = event["action"]
        details = json.loads(event["details_json"])
        features[0] = float(features[0]) + 1
        if action in {"file.upload_queued", "file.download"}:
            features[1] = float(features[1]) + (float(details.get("size_bytes", 0)) if action == "file.upload_queued" else 0)
        if action == "access_denied":
            features[2] = float(features[2]) + 1
        resource = event["resource_id"]
        if isinstance(resource, str):
            files = features[3]
            if isinstance(files, set):
                files.add(resource)
    for features in hourly.values():
        files = features[3]
        features[3] = float(len(files)) if isinstance(files, set) else 0.0
    peak_window, features = max(hourly.items(), key=lambda item: model.score(item[1])) if hourly else ("no recent activity", [0.0, 0.0, 0.0, 0.0])
    score = model.score(features)
    reasons = anomaly.reasons(features, baseline)
    finding = score >= 0.62
    if finding:
        with connect() as db:
            db.execute(
                "INSERT INTO anomaly_findings(id,tenant_id,user_id,score,reasons_json,event_count,created_at) VALUES(?,?,?,?,?,?,?)",
                (str(uuid.uuid4()), principal.tenant_id, principal.user_id, score, json.dumps(reasons), len(events), utc_now()),
            )
            audit(db, principal.tenant_id, principal.user_id, "analytics.finding_created", details={"score": round(score, 4), "event_count": len(events)})
    with connect() as db:
        findings = [dict(row) for row in db.execute(
                "SELECT id,user_id,score,reasons_json,event_count,created_at FROM anomaly_findings WHERE tenant_id=? AND user_id=? ORDER BY created_at DESC LIMIT 100",
            (principal.tenant_id, principal.user_id),
        ).fetchall()]
    for item in findings:
        item["reasons"] = json.loads(item.pop("reasons_json"))
    return {"model": "local-isolation-forest", "score": round(score, 4), "threshold": 0.62,
            "reasons": reasons, "event_count": len(events), "finding_created": finding,
            "peak_window_utc": peak_window, "features": dict(zip(anomaly.FEATURES, features, strict=True)),
            "action": "review only; no automatic blocking or deletion", "findings": findings}
