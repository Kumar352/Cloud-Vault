"""Small transactional SQLite store for the local, single-machine portfolio setup."""

from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterator


ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = Path(os.getenv("CLOUDVAULT_DATA_DIR", ROOT / "data" / "vault"))
DB_PATH = Path(os.getenv("CLOUDVAULT_DATABASE_PATH", DATA_DIR / "cloudvault.sqlite3"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
  id TEXT PRIMARY KEY,
  email TEXT NOT NULL UNIQUE,
  tenant_id TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS files (
  id TEXT PRIMARY KEY,
  tenant_id TEXT NOT NULL,
  owner_id TEXT NOT NULL REFERENCES users(id),
  name TEXT NOT NULL,
  created_at TEXT NOT NULL,
  UNIQUE(owner_id, name)
);
CREATE TABLE IF NOT EXISTS file_versions (
  id TEXT PRIMARY KEY,
  file_id TEXT NOT NULL REFERENCES files(id),
  version INTEGER NOT NULL,
  object_key TEXT NOT NULL UNIQUE,
  sha256 TEXT NOT NULL,
  size_bytes INTEGER NOT NULL,
  media_type TEXT NOT NULL,
  scan_state TEXT NOT NULL CHECK(scan_state IN ('queued','scanning','clean','infected','error')),
  scan_detail TEXT,
  created_at TEXT NOT NULL,
  UNIQUE(file_id, version)
);
CREATE TABLE IF NOT EXISTS shares (
  file_id TEXT NOT NULL REFERENCES files(id),
  user_id TEXT NOT NULL REFERENCES users(id),
  permission TEXT NOT NULL CHECK(permission IN ('read','write')),
  added_by TEXT NOT NULL REFERENCES users(id),
  created_at TEXT NOT NULL,
  PRIMARY KEY(file_id, user_id)
);
CREATE TABLE IF NOT EXISTS audit_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  tenant_id TEXT NOT NULL,
  user_id TEXT NOT NULL,
  action TEXT NOT NULL,
  resource_id TEXT,
  details_json TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_audit_tenant_created ON audit_events(tenant_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_user_id ON audit_events(user_id,id DESC);
CREATE TABLE IF NOT EXISTS assistant_usage (
  user_id TEXT NOT NULL,
  usage_date TEXT NOT NULL,
  request_count INTEGER NOT NULL,
  PRIMARY KEY(user_id, usage_date)
);
CREATE TABLE IF NOT EXISTS rag_chunks (
  id TEXT PRIMARY KEY,
  file_id TEXT NOT NULL,
  version_id TEXT NOT NULL,
  ordinal INTEGER NOT NULL,
  content TEXT NOT NULL,
  terms_json TEXT NOT NULL,
  UNIQUE(version_id, ordinal)
);
CREATE TABLE IF NOT EXISTS anomaly_findings (
  id TEXT PRIMARY KEY,
  tenant_id TEXT NOT NULL,
  user_id TEXT NOT NULL,
  score REAL NOT NULL,
  reasons_json TEXT NOT NULL,
  event_count INTEGER NOT NULL,
  created_at TEXT NOT NULL
);
"""


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def initialize() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with connect() as connection:
        connection.execute("PRAGMA journal_mode=WAL")
        connection.executescript(SCHEMA)
        now = utc_now()
        connection.executemany(
            "INSERT OR IGNORE INTO users(id,email,tenant_id,created_at) VALUES(?,?,?,?)",
            [
                ("alice", "alice@example.test", "demo", now),
                ("bob", "bob@example.test", "demo", now),
            ],
        )


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys=ON")
    connection.execute("PRAGMA busy_timeout=10000")
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def audit(connection: sqlite3.Connection, tenant_id: str, user_id: str, action: str,
          resource_id: str | None = None, details: dict[str, object] | None = None) -> None:
    """Record metadata only: callers must never pass content, tokens, or secrets."""
    connection.execute(
        "INSERT INTO audit_events(tenant_id,user_id,action,resource_id,details_json,created_at) VALUES(?,?,?,?,?,?)",
        (tenant_id, user_id, action, resource_id, json.dumps(details or {}, sort_keys=True), utc_now()),
    )
    connection.execute(
        "DELETE FROM audit_events WHERE user_id=? AND id NOT IN "
        "(SELECT id FROM audit_events WHERE user_id=? ORDER BY id DESC LIMIT 10000)",
        (user_id, user_id),
    )


initialize()
