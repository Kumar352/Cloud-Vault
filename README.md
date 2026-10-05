# CloudVault 2.0

CloudVault is a local-first security portfolio project for authenticated file storage and collaboration. Its Phase 1 implementation demonstrates encrypted quarantine, malware-scanned file versions, per-file sharing, audit trails, permission-filtered retrieval-augmented answers, and review-only anomaly detection.

## Phase status

**Phase 1 implementation is complete for the local portfolio scope.** The application uses a local OIDC provider, FastAPI, SQLite metadata, encrypted files stored on local disk, an optional ClamAV container, and local Ollama inference when available. Synthetic users and files are for learning only. See [the Phase 1 completion record](docs/phase-1-completion.md) and [the architecture](docs/architecture.md).

No AWS, Vercel, external model API, or hosted identity service is used by the application. The optional ClamAV image downloads current signature definitions when first started. AWS design remains documentation and disabled-by-default Terraform reference only; any later deployment requires a separate service-by-service estimate and review under the cost guardrails in [the Phase 2 plan](docs/phase-2-plan.md). The Phase 3 portfolio checklist records what is complete locally and what still depends on owner review or external access.

## Run the local app

Prerequisites: the workspace Node.js/pnpm and Python runtimes, existing app dependencies, and Docker Desktop only when using Dex/ClamAV. Local object storage and metadata need no Docker services.

If a regular PowerShell terminal cannot find Node or pnpm, add the bundled tools for that terminal:

    $env:PATH = "C:\Users\kumar\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin;C:\Users\kumar\.cache\codex-runtimes\codex-primary-runtime\dependencies\bin\fallback;" + $env:PATH

1. From the repository root, start local Dex and ClamAV when Docker is available:

   ```powershell
   docker compose --profile identity --profile scanner up -d dex clamav
   ```

   First ClamAV startup can take time while its free malware signatures are downloaded. Wait until ClamAV reports ready in its container logs.

2. In a second PowerShell window, start the API:

   ```powershell
   .\apps\api\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir apps\api --reload --host 127.0.0.1 --port 8000
   ```

3. In a third window, start the scan queue worker:

   ```powershell
   $env:PYTHONPATH = Join-Path (Get-Location) 'apps\api'
   .\apps\api\.venv\Scripts\python.exe -m app.worker
   ```

   Run that command from `apps\api` (or set `PYTHONPATH=apps\api` from the repository root).

4. In another window, start the web app from `apps\web`:

   ```powershell
   pnpm dev
   ```

5. Open [http://localhost:3000](http://localhost:3000) and sign in with one of the synthetic local users:

   | User | Password | Access example |
   |---|---|---|
   | `alice@example.test` | `password` | Owner of uploaded files; may share them |
   | `bob@example.test` | `password` | Read-only collaborator after Alice shares a file |

   This public sample password must never be reused. Use only synthetic files. Uploads are capped at 10 MiB and stay unavailable until ClamAV clears them. Downloads return only the latest clean version.

If Docker is not available, start the web app and API anyway. You can inspect the UI and API, but sign-in needs Dex and uploaded files remain quarantined because the scanner fails closed. The assistant responds with a grounded mock excerpt until Ollama is reachable.

Local guardrails cap uploads at 10 MiB each and 50 MiB total; each account can create 100 files, and each file keeps at most 20 versions. The scan queue accepts up to 25 queued files, the assistant accepts up to 50 questions per account per UTC day, and the audit history retains at most 10,000 rows per user.

## Local data and controls

- Runtime files, SQLite database, and the generated AES-GCM key are placed in ignored `data/vault/`; keep that directory out of Git and back up the key before any data migration.
- Use the installed local Ollama model `qwen3:1.7b-q4_K_M` if available. Hosted inference is not configured.
- Dex and ClamAV are optional Compose profiles; PostgreSQL/pgvector, S3Mock, and Redis are also opt-in comparison services and are not required by this SQLite/filesystem Phase 1 implementation.
- To stop optional containers after a demo: `docker compose stop dex clamav`.
- No Git push, cloud deployment, or Vercel publishing is part of this phase.

## Project references

- [Phase 1 completion record](docs/phase-1-completion.md)
- [Phase 2 plan and cost gate](docs/phase-2-plan.md)
- [Phase 3 proposed portfolio-release plan](docs/phase-3-plan.md)
- [Local demo walkthrough](docs/demo-guide.md)
- [Local troubleshooting](docs/troubleshooting.md)
- [Architecture and AWS target mapping](docs/architecture.md)
- [AWS Terraform reference blueprint](infra/aws/README.md)
- [Tools and connections checklist](docs/tools-and-connections.md)
- [Threat model](docs/threat-model.md)
- [Local development notes](docs/development.md)
- [API workflow](apps/api/README.md)
- [Web app](apps/web/README.md)

## License

License choice is pending owner review. Until a license is selected, do not assume the project is available for reuse.
