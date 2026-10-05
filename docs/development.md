# Development notes

## Local prerequisites

- Git is available in the workspace.
- Codex-bundled Node.js v24.19.0, pnpm v11.19.0, and Python 3.12.14 were installed under the local runtime cache during initial setup. Use the paths already configured in the Codex terminal; they are not system-wide runtimes.
- Next.js, React, and TypeScript packages are installed from the checked-in web package manifest/lockfile.
- The API uses FastAPI, Uvicorn, PyJWT, and cryptography from its local .venv. The Phase 1 feature modules use Python standard library modules in addition to those existing dependencies.
- Docker Desktop, Terraform, local Ollama and the Qwen3 1.7B model, PostgreSQL/pgvector, Redis, S3Mock, and ClamAV were installed or pulled in the earlier setup work. The optional containers are not needed for local metadata and object storage. Ollama is stopped unless explicitly started.
- The available machine inventory previously reported 16 GB RAM, no detected GPU/VRAM, and a 1.7B quantized Ollama model. Local inference can be slow on CPU.
- App runtime files, encrypted objects, SQLite data, and the generated storage key reside under ignored data/vault/.

Use synthetic identities and files only. Keep sources/ read-only and never add local data, model weights, keys, passwords, tokens, or real user documents to Git.

## Start the full local workflow

When Docker is available, start only the identity and antivirus services:

    docker compose --profile identity --profile scanner up -d dex clamav

ClamAV's first start downloads signature definitions. This step is free but uses bandwidth, disk, CPU, and memory; wait for initialization before scanning.

From the repository root, start the API:

    .\apps\api\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir apps\api --reload --host 127.0.0.1 --port 8000

From apps/api, start the scan worker in another terminal:

    .\.venv\Scripts\python.exe -m app.worker

From apps/web, start the web app in another terminal:

    pnpm dev

Then visit http://localhost:3000 and sign in using one of the synthetic users. Stop optional containers after the demo:

    docker compose stop dex clamav

If Docker is unavailable, the API's health route and web shell still start. Dex login cannot complete; ClamAV errors keep uploads quarantined. The assistant uses its grounded mock response unless local Ollama is running.

## Optional local Ollama

Use only the already-installed model. From the repository root in PowerShell:

    $env:OLLAMA_MODELS = Join-Path (Get-Location) 'data\ollama\models'
    & (Join-Path $env:LOCALAPPDATA 'Programs\Ollama\ollama.exe') serve

Keep the terminal open during use and press Ctrl+C to stop the server. The model is qwen3:1.7b-q4_K_M; the assistant calls Ollama at 127.0.0.1:11434 and falls back to a grounded mock when unavailable. Hosted model APIs are not configured.

## Phase 1 implementation boundaries

- SQLite stores metadata, ACLs, audit, version state, retrieval chunks, and anomaly findings.
- Local objects use AES-GCM with a generated key in the ignored data directory.
- Dex and ClamAV are opt-in Compose profiles and bind to loopback on the host.
- PostgreSQL/pgvector, S3Mock, and Redis are opt-in comparison services; the Phase 1 app does not use them.
- AWS and Vercel are not configured or deployed. Phase 2 is cost and deployment readiness planning first; see docs/phase-2-plan.md.
- All Phase 1 application changes remain local/uncommitted until reviewed. Do not push to a Git remote without a direct request.

## Verification commands

From the repository root:

    $env:PYTHONDONTWRITEBYTECODE = "1"
    .\apps\api\.venv\Scripts\python.exe -B -m unittest discover -s apps\api\tests -t apps\api -v

From apps/web:

    pnpm exec tsc --noEmit
    pnpm build

## Data handling and recovery

The generated local key and encrypted files must be backed up together. The key is not committed or managed by an HSM; loss of it makes stored uploads unrecoverable. Removing data/vault/ deletes local demo metadata and objects. This local prototype has no automatic backup or key-rotation mechanism.
