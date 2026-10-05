"""Single local queue worker that scans quarantined versions with ClamAV."""

from __future__ import annotations

import argparse
import time

from app.database import audit, connect
from app.rag import index_version
from app.scanner import scan_bytes
from app.storage import get, promote


def scan_pending_once() -> int:
    with connect() as db:
        queued = db.execute(
            "SELECT v.*,f.tenant_id,f.owner_id,f.name FROM file_versions v JOIN files f ON f.id=v.file_id WHERE v.scan_state='queued' ORDER BY v.created_at LIMIT 10"
        ).fetchall()
        for item in queued:
            db.execute("UPDATE file_versions SET scan_state='scanning',scan_detail=NULL WHERE id=? AND scan_state='queued'", (item["id"],))
    scanned = 0
    for item in queued:
        try:
            plaintext = get(item["object_key"])
            verdict = scan_bytes(plaintext)
            if verdict == "clean":
                promote(item["object_key"])
                state, detail = "clean", "ClamAV reported no detection"
                try:
                    index_version(item["file_id"], item["id"], item["name"], plaintext)
                except Exception as error:  # Extraction failure never changes the scanner verdict.
                    detail += f"; text indexing skipped ({type(error).__name__})"
            else:
                state, detail = "infected", "ClamAV detected a threat; object remains quarantined"
        except Exception as error:
            state, detail = "error", f"Scan unavailable or failed ({type(error).__name__}); object remains quarantined"
        with connect() as db:
            db.execute("UPDATE file_versions SET scan_state=?,scan_detail=? WHERE id=?", (state, detail, item["id"]))
            audit(db, item["tenant_id"], item["owner_id"], f"file.scan_{state}", item["file_id"],
                  {"version": item["version"], "size_bytes": item["size_bytes"]})
        scanned += 1
    return scanned


def main() -> None:
    parser = argparse.ArgumentParser(description="Scan queued CloudVault local uploads")
    parser.add_argument("--once", action="store_true", help="Process one queue batch and exit")
    parser.add_argument("--poll-seconds", type=int, default=3)
    args = parser.parse_args()
    while True:
        work = scan_pending_once()
        if args.once:
            print(f"Processed {work} queued version(s)")
            return
        if not work:
            time.sleep(max(1, min(args.poll_seconds, 60)))


if __name__ == "__main__":
    main()
