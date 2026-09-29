# Development notes

## Current environment check (30 September 2026)

- Git is available (`2.55.0.windows.5`).
- Docker/Docker Compose and Terraform were not found on the current command PATH.
- Codex's bundled Node.js `v24.19.0`, Python `3.12.14`, and pnpm `11.19.0` are available by absolute path under `C:\\Users\\kumar\\.cache\\codex-runtimes\\codex-primary-runtime\\dependencies`. They are agent runtimes, not global installations.
- The bundled Python currently has Pydantic, but FastAPI, Uvicorn, SQLAlchemy, scikit-learn, and pytest are not installed.
- No project Git repository existed at the start of Phase 1A.
- No RAM, GPU/VRAM, or free-disk inventory has been verified; select an Ollama model only after checking those resources.

No tools were installed and no external services were contacted as part of this check. Do not assume the bundled runtimes are suitable as a permanent development environment; verify project compatibility and use them only as needed.

## Phase 1A follow-up

1. Review and install the required local tools only if you choose to; prefer official installers and open-source editions.
2. Confirm hardware before selecting a local model size.
3. Add the Compose stack incrementally and verify each local service before connecting the application.
4. Keep hosted AI, AWS, Vercel, and remote Git publication disabled unless separately approved.
5. Choose a project license and repository visibility before publishing.

## Data handling

Use synthetic accounts and files. Never put `.env` files, credentials, model weights, or real user documents in Git. Keep synced ChatGPT project materials under `sources/` read-only and out of the application repository.
