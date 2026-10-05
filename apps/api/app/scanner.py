"""Minimal ClamAV INSTREAM client. Scanner errors are fail-closed."""

from __future__ import annotations

import os
import socket
import struct


def scan_bytes(data: bytes, *, host: str | None = None, port: int | None = None) -> str:
    host = host or os.getenv("CLAMAV_HOST", "127.0.0.1")
    port = port or int(os.getenv("CLAMAV_PORT", "3310"))
    with socket.create_connection((host, port), timeout=8) as stream:
        stream.settimeout(20)
        stream.sendall(b"zINSTREAM\0")
        for offset in range(0, len(data), 64 * 1024):
            chunk = data[offset:offset + 64 * 1024]
            stream.sendall(struct.pack("!I", len(chunk)) + chunk)
        stream.sendall(struct.pack("!I", 0))
        response = bytearray()
        while not response.endswith(b"\0") and len(response) < 4096:
            part = stream.recv(1024)
            if not part:
                break
            response.extend(part)
    result = response.decode("utf-8", "replace").strip("\0\r\n")
    if result.endswith(": OK"):
        return "clean"
    if result.endswith("FOUND"):
        return "infected"
    raise RuntimeError(f"ClamAV returned an unusable scan response: {result[:200]}")
