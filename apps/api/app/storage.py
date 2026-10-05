"""Encrypted local object store with explicit quarantine and clean namespaces."""

from __future__ import annotations

import os
import secrets
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.database import DATA_DIR


ROOT = DATA_DIR / "objects"
QUARANTINE = ROOT / "quarantine"
CLEAN = ROOT / "clean"
KEY_PATH = DATA_DIR / "local-storage.key"
MAGIC = b"CVLT1"


def _cipher() -> AESGCM:
    configured = os.getenv("CLOUDVAULT_STORAGE_KEY")
    if configured:
        import base64
        key = base64.urlsafe_b64decode(configured + "=" * (-len(configured) % 4))
        if len(key) not in {16, 24, 32}:
            raise RuntimeError("CLOUDVAULT_STORAGE_KEY must decode to 16, 24, or 32 bytes")
        return AESGCM(key)
    KEY_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not KEY_PATH.exists():
        try:
            descriptor = os.open(KEY_PATH, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError:
            pass
        else:
            with os.fdopen(descriptor, "wb") as key_file:
                key_file.write(secrets.token_bytes(32))
                key_file.flush()
                os.fsync(key_file.fileno())
    return AESGCM(KEY_PATH.read_bytes())


def _directory(clean: bool) -> Path:
    directory = CLEAN if clean else QUARANTINE
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def put(key: str, plaintext: bytes, *, clean: bool = False) -> None:
    nonce = secrets.token_bytes(12)
    sealed = MAGIC + nonce + _cipher().encrypt(nonce, plaintext, key.encode())
    (_directory(clean) / f"{key}.blob").write_bytes(sealed)


def get(key: str, *, clean: bool = False) -> bytes:
    source = _directory(clean) / f"{key}.blob"
    sealed = source.read_bytes()
    if not sealed.startswith(MAGIC) or len(sealed) < len(MAGIC) + 12:
        raise ValueError("Stored object header is invalid")
    nonce = sealed[len(MAGIC):len(MAGIC) + 12]
    return _cipher().decrypt(nonce, sealed[len(MAGIC) + 12:], key.encode())


def promote(key: str) -> None:
    source = QUARANTINE / f"{key}.blob"
    destination_dir = _directory(True)
    destination = destination_dir / source.name
    if not source.exists():
        raise FileNotFoundError("Quarantined object was not found")
    source.replace(destination)


def exists(key: str, *, clean: bool = False) -> bool:
    return (_directory(clean) / f"{key}.blob").is_file()


def delete(key: str) -> None:
    for directory in (QUARANTINE, CLEAN):
        path = directory / f"{key}.blob"
        if path.exists():
            path.unlink()
