# CloudVault API

FastAPI implements the local CloudVault workflow. The supported local dataset is intentionally small and synthetic.

## Start services

From the repository root, when Docker is available:

```powershell
docker compose --profile identity --profile scanner up -d dex clamav
```

Then run the API from the repository root:

```powershell
.\apps\api\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir apps\api --reload --host 127.0.0.1 --port 8000
```

Run the durable, SQLite-backed scan queue worker in a separate PowerShell window from `apps\api`:

```powershell
.\.venv\Scripts\python.exe -m app.worker
```

The worker processes batches of up to ten quarantined uploads, asks local ClamAV to scan them, promotes only clean versions, and indexes supported text files. `--once` processes one batch and exits. Scanner connection errors leave the object in quarantine with an `error` state; the owner can queue a retry through the API. Infected objects remain quarantined and cannot be downloaded.

## API workflow

Use `http://localhost:8000/docs` for the PKCE OIDC flow and API details. The web interface at `http://localhost:3000` offers the same core actions.

1. Sign in with Dex using `alice@example.test` or `bob@example.test`; the sample password is `password` for both accounts. Never use these public credentials outside local development.
2. `POST /files` uploads raw bytes using the `X-File-Name` header. The API limits uploads to 10 MiB, encrypts them with AES-GCM, stores them under quarantine, creates a version and audit event, and returns `202`.
3. The worker scans queued versions. A clean version is promoted into the clean namespace. A detection or scanner error stays quarantined.
4. Only the latest clean version can be downloaded from `GET /files/{file_id}/download`. `GET /files/{file_id}/versions` lists scan states and version metadata.
5. Owners can grant/revoke `read` or `write` access to the other seeded user through `/files/{file_id}/shares`. Bob's shared-file RAG retrieval is limited by the current share ACL.
6. `POST /assistant/ask` searches clean, text-indexed files the current user can access. It calls the local Ollama API if available; otherwise, it returns excerpts as a clearly labeled grounded mock answer. Every result includes file/version/chunk citations. It never calls a hosted model provider.
7. `GET /audit` returns only the current user's metadata events. `POST /analytics/analyze` scores that user's recent audit pattern and stores unusual activity for review only. `GET /analytics/anomaly-evaluation` reports synthetic baseline metrics.

## Local configuration and data

Local guardrails cap uploads at 10 MiB each, 50 MiB of stored versions per tenant, 100 files per owner, 20 versions per file, 25 queued scans, and 50 assistant questions per user per UTC day. At most 10,000 audit rows are retained per user. Owners can permanently delete a file and all its versions from the workbench.

- Dex defaults: `CLOUDVAULT_OIDC_ISSUER=http://localhost:5556/dex`, audience `cloudvault-api`, local JWKS `http://localhost:5556/dex/keys`.
- API origin is loopback-only. CORS permits the local web app at `http://localhost:3000`.
- `CLOUDVAULT_DATA_DIR` selects the ignored local runtime directory. Default: repository `data/vault/`.
- A random 256-bit AES-GCM key is generated at `data/vault/local-storage.key` for the local file store. Keep it private and out of Git; loss of this key makes existing local uploads unreadable. `CLOUDVAULT_STORAGE_KEY` may instead provide a base64url-encoded 16-, 24-, or 32-byte key for a controlled local setup.
- RAG reads UTF-8 `.txt`, `.md`, `.csv`, and `.json` files (up to 500,000 characters), indexes bounded overlapping chunks, and ranks them locally with BM25. Other formats can be stored and scanned but are not text-indexed.
- Ollama defaults to `http://127.0.0.1:11434`, model `qwen3:1.7b-q4_K_M`; override with `OLLAMA_BASE_URL` / `OLLAMA_CHAT_MODEL` if needed.
- SQLite metadata, local objects, and the key are in ignored `data/`. Back them up together if you choose to keep test data.

## Checks

From the repository root:

```powershell
$env:PYTHONDONTWRITEBYTECODE = "1"
.\apps\api\.venv\Scripts\python.exe -B -m unittest discover -s apps\api\tests -t apps\api -v
```

This project is a local portfolio prototype. It is not a production file-storage service, and local filesystem encryption is not a substitute for AWS KMS, managed identity, backups, or a threat-reviewed production design.
