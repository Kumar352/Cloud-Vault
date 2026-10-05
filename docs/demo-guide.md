# CloudVault local portfolio walkthrough

This is a short, synthetic-data walkthrough of the local implementation. It uses no AWS account, external identity provider, hosted model, or public upload endpoint. It is a portfolio demo, not a production service.

## What the walkthrough demonstrates

| Part | What to show | Skill demonstrated |
|---|---|---|
| Identity | Sign in locally as Alice, then Bob | OIDC authorization code with PKCE, verified JWT claims |
| Secure storage | Upload a generated `.txt` file; show it unavailable while quarantined | Size caps, AES-GCM at rest, quarantine/clean separation |
| Malware workflow | Run the local scan worker and show clean promotion, or show fail-closed error if ClamAV is unavailable | Queue processing, antivirus protocol, fail-closed handling |
| Collaboration | Alice shares one clean file with Bob; Bob can retrieve it; revoke access and retry | Per-request authorization and revocation |
| AI/RAG | Ask about a fact in the shared text and show citations; use local Ollama if already running or the grounded mock | ACL-filtered retrieval, bounded context, citations, local inference fallback |
| Cybersecurity audit | Review metadata-only events for Alice and Bob | Auditing without storing document content in event records |
| ML anomaly review | Run analysis and show a finding stays advisory | Isolation Forest over synthetic features; no automatic blocking |

## Before starting

- Use only the synthetic accounts in the root README and generated, non-sensitive text.
- Check [development prerequisites](development.md). Docker is needed for the complete Dex/ClamAV flow. If Docker is unavailable, the login and scan parts cannot be demonstrated; report them as unverified rather than claiming success.
- Optional containers download their images, and ClamAV downloads signature data on first start. These consume local bandwidth, disk, memory, and electricity. There is no AWS charge.
- Ollama is optional. The app uses a grounded mock when the loopback model is unavailable. Never substitute a remote model URL or real customer document.

## Walkthrough sequence

1. Start Dex and ClamAV using the local-only commands in the root README. Wait for the scanner to be ready.
2. Start the API, scan worker, and Next.js web app in separate terminals.
3. Sign in as Alice and upload a small generated text file, for example: `The CloudVault sample key rotation interval is 90 days.`
4. Show the file as pending/quarantined. Start or observe the worker; only a clean scan should make the file downloadable and searchable.
5. Share the clean file with Bob as read-only. Sign out and sign in as Bob. Ask “What is the sample key rotation interval?” and inspect the file/version/chunk citation.
6. Revoke Bob's share as Alice. Sign in as Bob again and show the file is no longer visible or retrievable.
7. Review each user's audit events. Run anomaly analysis and explain that the generated synthetic score is advisory and does not alter access.
8. Sign out and stop the app processes and optional containers. Keep no local data unless you intentionally want it for another synthetic demo.

## Stop and reset

Stop `pnpm dev`, Uvicorn, the worker, and Ollama with Ctrl+C in their terminals. Stop the optional Compose containers from the repository root:

```powershell
docker compose stop dex clamav
```

To permanently remove local demonstration state (accounts, metadata, encrypted test objects, and the generated encryption key), first stop all app processes and containers, then remove `data/vault/` from PowerShell:

```powershell
Remove-Item -LiteralPath .\data\vault -Recurse -Force
```

This reset is destructive to local demo files. Do not remove the directory if you need those test files; copy the encrypted objects and their key together before any intentional migration. Docker's Dex and ClamAV data volumes are separate and can be left stopped between demos.

## What this demo does not prove

- Docker-dependent login and live antivirus promotion have not been verified in this environment if Docker cannot be reached.
- A clean test scan is not proof that ClamAV detects every threat. Do not upload real malware or real documents.
- The local model is small and CPU-only on the recorded machine; response quality and speed are not production benchmarks.
- Synthetic anomaly metrics do not establish detection performance on real activity.
- SQLite, local disk encryption, public test passwords, and browser session storage are not production-grade managed services or account controls.
- AWS mapping and estimates are design artifacts. This demo does not deploy or validate AWS security controls.
