# CloudVault tools and connections checklist

Checked 2026-10-05. The target is a reproducible local portfolio, published source, and documented AWS design. It does not require a live cloud service. The default operating cost target is $0 recurring; local electricity, bandwidth, and already-owned hardware are outside that figure.

## Required to finish and publish the portfolio

| Item | What CloudVault uses it for | Current status | Next step |
|---|---|---|---|
| Codex workspace | Edit and review the project in the existing checkout | Connected at the CloudVault project path | Continue here; keep `sources/` read-only and private account notes ignored. |
| Git + Git Credential Manager | Local version control and authenticated GitHub push | Git and Credential Manager are installed. `origin` now points to `https://github.com/Kumar352/Cloud-Vault.git`; a read-only Git remote query succeeded and returned no `main` branch. Local write authentication is not confirmed. | Resolve/verify authenticated push after reviewing the final publishable file list. Never paste a token into chat or a file. |
| GitHub | Public source repository | GitHub connector is authenticated as `Kumar352`; repository metadata is readable and reports push permission. Repository is public and empty. A previous connector write returned HTTP 403. | Use the configured local remote and Credential Manager to publish only after final review. Do not publish `sources/`, `data/`, `.env*` secrets, model files, or generated uploads. |
| Node.js + pnpm | Next.js + TypeScript web app | Bundled Node 24.19.0 and pnpm 11.19.0 are available; web dependencies and lockfile are present. | No extra installation needed. |
| Python | FastAPI API, scanner worker, and local anomaly model | App virtual environment has Python 3.12.14, FastAPI, Uvicorn, and PyJWT installed. | No extra installation needed. |
| Docker Desktop + engine | Optional local Dex identity and ClamAV malware scanning | Docker engine 29.8.1 connected. Dex OIDC discovery and ClamAV PING/PONG both succeeded. Both CloudVault containers were stopped after the check; required images are cached locally. | Start `dex` and `clamav` with the documented Compose profiles for a walkthrough. Pulling images uses bandwidth and disk, not a cloud service charge. |
| Ollama | Real local model for the RAG assistant; grounded mock is fallback | Ollama executable and `qwen3:1.7b-q4_K_M` model are present. A bounded local inference returned `LOCAL MODEL OK`; the server was stopped after the check. | Start the local Ollama server for a walkthrough; keep hosted inference disabled. |

## Needed only for the AWS design validation

| Item | What it is for | Current status | Next step |
|---|---|---|---|
| Terraform CLI | Format and validate `infra/aws/` reference code; it does not itself make the app cloud-ready | Terraform 1.16.5 is installed in ignored `.tools/`; its official archive checksum was verified, signed AWS/random providers were downloaded, and `terraform validate` passed. | No system-wide install. Never run `apply` as part of the zero-cost project. |
| AWS Pricing Calculator | Estimate a specific proposed deployment | Public calculator is available without AWS credentials. | Use only if considering deployment; enter exact region, runtime, log, storage, scan, and transfer limits. Save the estimate and include taxes/FX and the $0-credit case. |
| AWS account access | Verify account credit and review existing usage | AWS Data Analytics connector is connected, but its STS identity resolves to the AWS account root. Read-only account review on 2026-10-05 found the returned promotional credits expired, budget alerts had no subscriber, and unrelated billable resources existed. | Do not provision with root credentials. If cloud work is later approved, use a dedicated least-privilege role and first resolve existing spend/alerts. Keep CloudVault local unless a new exact estimate is reviewed. |

The AWS connector is not a substitute for the AWS console's full service coverage or the Pricing Calculator. The optional Terraform blueprint covers only example S3 buckets, SQS, CloudWatch logs, and optional Cognito/GuardDuty. It does not provision the web/API compute, scanner worker, PostgreSQL, VPC, KMS, CloudTrail, budget alerts, or RAG inference.

## Connected but not required for this project goal

| Tool | Current status | Decision |
|---|---|---|
| Vercel | Vercel connector authenticated; account is on Hobby and has no CloudVault project. | Do not connect/deploy this frontend for the local portfolio. The app needs a reachable API, identity provider, and scanner; hosting only Next.js would not provide those. Hobby is limited to personal/non-commercial use under current terms. |
| GitHub Actions | Not configured | Optional. Avoid deployment workflows and external CI until the workflow, permissions, and any usage/storage implications are reviewed. Local checks are enough for the current $0 target. |
| PostgreSQL/pgvector, Redis, S3Mock | Compose definitions exist as optional comparison services, but Phase 1 does not use them. | Not needed to run or demonstrate the implemented local app. |
| Figma, Notion, email/chat, paid hosted AI, VirusTotal, hosted malware scanning | No project integration configured or required | Do not add accounts or subscriptions for this portfolio. The current visual app, docs, ClamAV, Ollama, and mock response cover the intended learning scope locally. |

## Keep free of recurring charges

- GitHub Free supports public repositories; standard GitHub Actions runner usage is free for public repositories under current GitHub documentation. Actions are still not required for this project.
- Docker Desktop is free for personal use, education, non-commercial open-source projects, and small businesses that meet Docker's stated limits. Check the official license if the use context changes.
- Terraform CLI is distributed by HashiCorp; installing the CLI does not create AWS resources. Initializing Terraform downloads provider plugins.
- Ollama local inference avoids hosted model-token charges. Model downloads use local disk and bandwidth.
- Vercel Hobby is listed at $0/month but is restricted to personal/non-commercial use; additional services or usage can be chargeable.
- AWS promotional credits are eligibility-, service-, and expiry-dependent and do not create a hard spending cap. The account-specific records reviewed on 2026-10-05 were expired, so plan AWS as out-of-pocket unless the live billing console later confirms otherwise.

## Connection order

1. Confirm local tools: Git/GCM, Node/pnpm, Python, Docker engine, and Ollama/model.
2. Resolve GitHub local-push authentication and set the `origin` remote; keep secrets out of the repository.
3. Validate the publishable file list and local project checks before pushing.
4. Keep AWS in documentation-only mode. Use a least-privilege AWS role, a current estimate, a tested alert destination, and reviewed teardown only if the owner later selects a cloud demonstration.
5. Keep Vercel and paid third-party tools disconnected unless a concrete architecture change requires them.

## Official references

- [GitHub plans and Actions pricing](https://github.com/pricing) and [Actions billing rules](https://docs.github.com/en/billing/concepts/product-billing/github-actions).
- [Docker Desktop license](https://docs.docker.com/subscription-billing/desktop-license/).
- [Terraform CLI installation](https://developer.hashicorp.com/terraform/tutorials/aws-get-started/install-cli).
- [Ollama for Windows](https://ollama.com/download/windows).
- [Vercel pricing](https://vercel.com/pricing) and [Hobby plan terms](https://vercel.com/legal/terms).
- [AWS Pricing Calculator guide](https://docs.aws.amazon.com/pricing-calculator/latest/userguide/getting-started.html), [AWS credit FAQ](https://aws.amazon.com/free/free-tier-faqs/), and [promotional credit terms](https://aws.amazon.com/awscredits/).
