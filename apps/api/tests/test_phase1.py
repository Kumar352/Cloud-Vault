from __future__ import annotations

import os
import random
import socket
import tempfile
import threading
import unittest
import asyncio
from unittest.mock import patch

from fastapi import HTTPException
from starlette.requests import Request


_test_data = tempfile.TemporaryDirectory(prefix="cloudvault-tests-")
os.environ["CLOUDVAULT_DATA_DIR"] = _test_data.name

from app import anomaly  # noqa: E402
from app.database import connect, utc_now  # noqa: E402
from app.rag import _ollama_answer, index_version, retrieve  # noqa: E402
from app.scanner import scan_bytes  # noqa: E402
from app.storage import CLEAN, QUARANTINE, get, promote, put  # noqa: E402
from app.auth import Principal  # noqa: E402
from app.vault import ShareRequest, _file, delete_file, grant_share, list_shares, revoke_share, retry_scan, upload_file  # noqa: E402
from app.worker import scan_pending_once  # noqa: E402


class StorageAndRetrievalTests(unittest.TestCase):
    def setUp(self) -> None:
        with connect() as db:
            db.execute("DELETE FROM rag_chunks")
            db.execute("DELETE FROM shares")
            db.execute("DELETE FROM file_versions")
            db.execute("DELETE FROM files")
            db.execute("DELETE FROM audit_events")

    @property
    def alice(self) -> Principal:
        return Principal("alice", "alice-sub", "alice@example.test", "demo")

    @property
    def bob(self) -> Principal:
        return Principal("bob", "bob-sub", "bob@example.test", "demo")

    @staticmethod
    def request_for_upload(name: str, content: bytes) -> Request:
        async def receive():
            return {"type": "http.request", "body": content, "more_body": False}
        headers = [(b"x-file-name", name.encode()), (b"content-type", b"text/plain"),
                   (b"content-length", str(len(content)).encode())]
        scope = {"type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1",
                 "method": "POST", "scheme": "http", "path": "/files", "raw_path": b"/files",
                 "query_string": b"", "headers": headers, "server": ("test", 80), "client": ("test", 1)}
        return Request(scope, receive)

    def test_encryption_and_quarantine_promotion_are_separate(self) -> None:
        key = "phase1-storage-check"
        content = b"synthetic secret text"
        put(key, content)
        self.assertNotEqual((QUARANTINE / f"{key}.blob").read_bytes(), content)
        self.assertEqual(get(key), content)
        self.assertFalse((CLEAN / f"{key}.blob").exists())
        promote(key)
        self.assertFalse((QUARANTINE / f"{key}.blob").exists())
        self.assertEqual(get(key, clean=True), content)

    def test_retrieval_obeys_share_acl_and_clean_status(self) -> None:
        now = utc_now()
        first_id, first_version = "file-shared", "version-shared"
        private_id, private_version = "file-private", "version-private"
        with connect() as db:
            db.executemany(
                "INSERT INTO files(id,tenant_id,owner_id,name,created_at) VALUES(?,?,?,?,?)",
                [(first_id, "demo", "alice", "sharing-guide.txt", now),
                 (private_id, "demo", "alice", "private-secret.txt", now)],
            )
            db.executemany(
                "INSERT INTO file_versions(id,file_id,version,object_key,sha256,size_bytes,media_type,scan_state,created_at) VALUES(?,?,?,?,?,?,?,?,?)",
                [(first_version, first_id, 1, "object-shared", "0" * 64, 50, "text/plain", "clean", now),
                 (private_version, private_id, 1, "object-private", "1" * 64, 50, "text/plain", "clean", now)],
            )
            db.execute("INSERT INTO shares(file_id,user_id,permission,added_by,created_at) VALUES(?,?,?,?,?)",
                       (first_id, "bob", "read", "alice", now))
        index_version(first_id, first_version, "sharing-guide.txt", b"The secure sharing guide explains account access and encrypted versions.")
        index_version(private_id, private_version, "private-secret.txt", b"The hidden phrase is cobalt hummingbird.")
        visible = retrieve("secure sharing encrypted versions", "bob", "demo")
        hidden = retrieve("cobalt hummingbird", "bob", "demo")
        self.assertEqual([item["filename"] for item in visible], ["sharing-guide.txt"])
        self.assertEqual(hidden, [])

    def test_model_adapter_refuses_non_loopback_hosts(self) -> None:
        with patch.dict(os.environ, {"OLLAMA_BASE_URL": "https://example.invalid"}), patch(
            "urllib.request.urlopen", side_effect=AssertionError("remote model call must not happen")
        ):
            self.assertIsNone(_ollama_answer("question", [{"filename": "x.txt", "version": 1, "chunk": 1, "text": "local text"}]))

    def test_owner_grants_and_revokes_collaborator_access(self) -> None:
        with connect() as db:
            db.execute("INSERT INTO files(id,tenant_id,owner_id,name,created_at) VALUES(?,?,?,?,?)",
                       ("share-api-file", "demo", "alice", "team.txt", utc_now()))
        result = grant_share("share-api-file", ShareRequest(email="bob@example.test", permission="read"), self.alice)
        self.assertEqual(result["permission"], "read")
        self.assertEqual(_file("share-api-file", self.bob)["owner_id"], "alice")
        self.assertEqual(list_shares("share-api-file", self.alice)[0]["email"], "bob@example.test")
        revoke_share("share-api-file", "bob", self.alice)
        with self.assertRaises(HTTPException) as error:
            _file("share-api-file", self.bob)
        self.assertEqual(error.exception.status_code, 404)

    def test_upload_stays_quarantined_until_worker_marks_clean(self) -> None:
        content = b"Synthetic security plan for local retrieval."
        result = asyncio.run(upload_file(self.request_for_upload("plan.txt", content), self.alice))
        self.assertEqual(result["scan_state"], "queued")
        self.assertEqual(get(result["version_id"]), content)
        with patch("app.worker.scan_bytes", return_value="clean"):
            self.assertEqual(scan_pending_once(), 1)
        with connect() as db:
            version = db.execute("SELECT scan_state,object_key FROM file_versions WHERE id=?", (result["version_id"],)).fetchone()
        self.assertEqual(version["scan_state"], "clean")
        self.assertEqual(get(version["object_key"], clean=True), content)
        self.assertEqual(retrieve("security plan", "alice", "demo")[0]["filename"], "plan.txt")

    def test_infected_or_unavailable_scan_stays_blocked_and_can_retry_error(self) -> None:
        result = asyncio.run(upload_file(self.request_for_upload("sample.txt", b"Synthetic sample."), self.alice))
        with patch("app.worker.scan_bytes", return_value="infected"):
            self.assertEqual(scan_pending_once(), 1)
        with connect() as db:
            state = db.execute("SELECT scan_state,object_key FROM file_versions WHERE id=?", (result["version_id"],)).fetchone()
        self.assertEqual(state["scan_state"], "infected")
        self.assertTrue((QUARANTINE / f"{state['object_key']}.blob").exists())
        self.assertFalse((CLEAN / f"{state['object_key']}.blob").exists())

        second = asyncio.run(upload_file(self.request_for_upload("retry.txt", b"Retry after scanner startup."), self.alice))
        with patch("app.worker.scan_bytes", side_effect=OSError("offline")):
            self.assertEqual(scan_pending_once(), 1)
        queued = retry_scan(second["version_id"], self.alice)
        self.assertEqual(queued["scan_state"], "queued")

    def test_owner_can_remove_file_and_all_versions(self) -> None:
        result = asyncio.run(upload_file(self.request_for_upload("remove.txt", b"Synthetic disposable data."), self.alice))
        with connect() as db:
            version = db.execute("SELECT object_key FROM file_versions WHERE id=?", (result["version_id"],)).fetchone()
        with self.assertRaises(HTTPException) as denied:
            delete_file(result["file_id"], self.bob)
        self.assertEqual(denied.exception.status_code, 404)
        delete_file(result["file_id"], self.alice)
        self.assertFalse((QUARANTINE / f"{version['object_key']}.blob").exists())
        with connect() as db:
            self.assertIsNone(db.execute("SELECT id FROM files WHERE id=?", (result["file_id"],)).fetchone())


class ScannerProtocolTests(unittest.TestCase):
    def test_instream_clean_response(self) -> None:
        server = socket.socket()
        server.bind(("127.0.0.1", 0))
        server.listen(1)
        port = server.getsockname()[1]

        def serve() -> None:
            connection, _ = server.accept()
            with connection:
                command = bytearray()
                while not command.endswith(b"\0"):
                    command.extend(connection.recv(1))
                while True:
                    header = bytearray()
                    while len(header) < 4:
                        header.extend(connection.recv(4 - len(header)))
                    size = int.from_bytes(header, "big")
                    if size == 0:
                        break
                    remaining = size
                    while remaining:
                        part = connection.recv(remaining)
                        if not part:
                            break
                        remaining -= len(part)
                connection.sendall(b"stream: OK\0")
            server.close()

        thread = threading.Thread(target=serve, daemon=True)
        thread.start()
        self.assertEqual(scan_bytes(b"safe synthetic content", host="127.0.0.1", port=port), "clean")
        thread.join(timeout=2)


class AnomalyModelTests(unittest.TestCase):
    def test_isolation_forest_and_synthetic_evaluation(self) -> None:
        result = anomaly.synthetic_evaluation()
        self.assertEqual(result["recall"], 1.0)
        self.assertEqual(result["synthetic_anomalies"], 4)
        self.assertLessEqual(result["false_positive_rate"], 0.25)
        rng = random.Random(8)
        baseline = [[rng.gauss(3, 1), rng.gauss(30_000, 8_000)] for _ in range(128)]
        model = anomaly.IsolationForest(trees=24, seed=3).fit(baseline)
        self.assertGreater(model.score([100, 2_000_000]), model.score([3, 30_000]))


if __name__ == "__main__":
    unittest.main()
