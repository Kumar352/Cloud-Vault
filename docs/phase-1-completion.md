# Phase 1 completion record

**Status: local Phase 1 implementation complete.** This record covers the complete local portfolio scope agreed for CloudVault 2.0: identity and permissions, secure versioned files, quarantine and scanning, collaboration and audit, permission-aware RAG, ML anomaly review, and the AWS target map. It does not authorize a cloud deployment.

## Delivered

| Area | Delivered behavior |
|---|---|
| Local application | Next.js workbench and FastAPI API; no cloud dependency |
| Identity | Dex OIDC authorization-code flow with PKCE, synthetic Alice/Bob accounts, signed JWT/JWKS validation |
| Authorization | Current owner/read/write share checks on each file, download, and retrieval; inaccessible resources return 404 |
| Storage | 10 MiB upload cap, SHA-256 metadata, AES-GCM encryption, persisted version rows, separate quarantine and clean folders |
| Malware lifecycle | SQLite-backed scan queue, ClamAV INSTREAM worker, fail-closed errors, clean-only promotion/download, retry for scanner errors |
| Collaboration | Same-tenant synthetic read/write grants and revocation; owner can inspect current grants |
| Audit | Metadata-only upload, scan, download, sharing, query, access-denial, and analytics events; user sees their own event list |
| AI assistant | Clean text indexing for UTF-8 TXT/Markdown/CSV/JSON; BM25 retrieval with current ACLs, version/chunk citations, local Ollama generation, grounded mock fallback |
| ML security | Local Isolation Forest, deterministic synthetic evaluation metrics, explainable reasons, persisted review-only findings |
| Cloud learning | AWS service mapping and cost/deployment guardrail recorded in the architecture and Phase 2 plan |
| User interface | Browser PKCE sign-in, account session, file upload/list/download/share, assistant, activity, and anomaly review |
| Resource guardrails | 25 queued scans, 50 assistant questions per user/day, 10,000 audit rows per user, retry on scanner errors, owner file/version deletion |

## Boundaries and known gaps

- The demo users and sample password are public fixtures. There is no production account registration, recovery, MFA, or external identity configuration.
- SQLite and local files are single-machine choices, not a scalable or highly available service. Database migration/backup/restore to managed PostgreSQL remains Phase 2 architecture work.
- The AES-GCM key is kept on the same machine under ignored data. This demonstrates encryption behavior but does not provide KMS-style key separation, key rotation, or disaster recovery.
- The scanner image needs ClamAV signature updates. If ClamAV is not running, scan failures remain quarantined. Live antivirus signature behavior could not be exercised in the Codex workspace because Docker pipe access is denied.
- Text indexing supports UTF-8 .txt, .md, .csv, and .json only. Retrieval is lexical BM25 rather than semantic vector search. PDF/Office extraction, semantic embeddings, and pgvector are future improvements.
- The optional Ollama model is local. If it is stopped or missing, the assistant returns grounded source excerpts through the mock path. No hosted inference is configured.
- Synthetic anomaly metrics validate the demo fixture, not real-world quality. Findings are never an automated enforcement mechanism.
- The assistant keeps access tokens in browser sessionStorage for this local demo. A production design needs a reviewed secure server-side session or equivalent.

## Verification

- API unit checks cover JWT claim/signature handling, resource ACL behavior, encrypted quarantine/promotion, ACL-filtered retrieval, the ClamAV INSTREAM protocol, and Isolation Forest scoring/evaluation.
- Frontend TypeScript checking and the optimized Next.js production build passed.
- FastAPI health and OpenAPI routes responded locally during implementation.
- Full live Dex browser sign-in and real ClamAV signature scanning were not verified in this task because Dex was stopped and this workspace was denied Docker engine access.
- No AWS account was queried, no resources were created, no paid API was used, and no Git remote push was made.

## Starting point for Phase 2

Phase 2 prepares the local demonstration and an account-specific cost/readiness review. The repository contains the estimate assumptions and required account checks, but the account's live AWS credits, eligibility, Region, budgets, and quotas have not been verified here. Any resource creation remains gated on that evidence and review of the concrete estimate. See the Phase 2 plan. No Phase 3 specification was present, so the proposed portfolio-release scope is documented separately in `phase-3-plan.md`.
