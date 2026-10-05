# Local setup troubleshooting

All checks below are local. They do not contact AWS or hosted model services.

## `localhost:3000` says the connection was refused

The web development server is not running, exited with an error, or chose another port. Start it from `apps/web` with `pnpm dev` and leave that terminal open. Read the first error shown in the terminal; Next.js prints the actual local URL if port 3000 is busy. Stop the old process or open the printed URL. Start the API separately on port 8000 if the page needs its health endpoint.

## Docker Desktop or Compose is unavailable

Open Docker Desktop and wait for its engine to report ready. In PowerShell, run `docker info` and then `docker compose ps` from the repository root. If `docker info` reports a named-pipe/engine error, Compose cannot start Dex or ClamAV. Do not change Windows virtualization or security settings as a workaround without understanding the system impact. The API health route and web shell can still run without Docker, but OIDC login and live malware scanning cannot be demonstrated; uploads remain quarantined when scanning is unavailable.

## Dex image, startup, or login fails

Check that port 5556 is free and inspect `docker compose logs dex`. A first-time image pull needs access to the container registry. If pulling fails, wait for the registry/network to recover and retry; do not switch to an unpinned or untrusted identity image. Confirm that API and web OIDC issuer settings both use `http://localhost:5556/dex`, the client ID is `cloudvault-api`, and the callback URL is exactly the one configured in `infra/dex/config.yaml`. The sample password is only for the synthetic local account.

## ClamAV is starting, unreachable, or reports a scan error

The first ClamAV start downloads signature definitions and may take several minutes. Check `docker compose logs -f clamav` until the daemon reports ready and confirm local port 3310 is available. The API/worker fail closed: a scan error does not make an object downloadable. Use the app's retry action after the scanner is healthy. Never edit the database or move a quarantined object manually to mark it clean.

## The assistant uses a mock instead of Ollama

That is the expected behavior when the local model server is stopped or unreachable. Check `ollama list`, start the locally installed Ollama server, and confirm it listens on `127.0.0.1:11434`. The configured model must already be installed; a model download uses local disk and network but no hosted inference API. The assistant is deliberately configured for loopback only. Do not change it to a public or third-party model endpoint to fix a local issue.

## API health or browser requests fail

Open `http://127.0.0.1:8000/health` while the API terminal is running. If it fails, inspect the API terminal and confirm port 8000 is free. Browser requests originate from `http://localhost:3000`; the API's local CORS allowlist uses that exact origin. `localhost` and `127.0.0.1` are not interchangeable for every browser origin check.

## Dependency command cannot find TypeScript or Next.js

Run commands from the correct app folder (`apps/web`) and check `node_modules/.bin/`. The repository includes `pnpm-lock.yaml`; if dependencies are missing and the pnpm store already has them, try `pnpm install --offline --frozen-lockfile`. If the offline install says packages are unavailable, stop and review what would need to be downloaded before retrying. Do not commit `node_modules`, `.next`, `.pnpm-store`, or package caches.

## Local data or encryption key problem

The default database, encrypted objects, and generated storage key are under ignored `data/vault/`. The encrypted files cannot be read without the matching key. Back up the files and key together before intentionally moving data. Deleting `data/vault/` permanently removes the local demo dataset and key; see the reset warning in `demo-guide.md`.

## Still stuck

Save the first relevant error from the local terminal, the affected step, and whether Docker/Ollama was running. Remove tokens, file contents, personal data, keys, and environment values before sharing logs. Do not paste the contents of `.env.local`, `data/vault/`, or the ignored private AWS readiness note into GitHub issues.
