# CloudVault threat model

This is a portfolio-learning threat model, not a security certification or production approval.

## Assets

- User identity, browser access token, sharing grants, and ACL metadata.
- Uploaded bytes, versions, encryption key, scan disposition, extracted text, and indexed chunks.
- Audit events, anomaly findings, assistant prompts, answers, and citations.
- Local services, application configuration, and future cloud account/credits.

## Trust boundaries

- Browser and local Dex to the API.
- User and tenant boundary within metadata and object storage.
- Encrypted quarantine versus encrypted clean storage.
- ClamAV worker and file parser handling hostile bytes.
- Retrieved document text entering Ollama's prompt.
- Local computer versus optional remote AWS services.

## Implemented controls and remaining risks

| Threat | Phase 1 control | Remaining limitation |
|---|---|---|
| Forged or wrong-API token | RS256 signature/JWKS, issuer, audience, expiry, issued-at and subject validation | Local public test users/password; no production account lifecycle |
| Cross-user file access | Per-request tenant, owner, share, and permission checks; 404 for inaccessible files | Same-machine SQLite prototype; needs security review and adversarial tests |
| Oversized upload | 10 MiB cap from Content-Length and streaming body checks | Resource controls and multi-file quotas remain basic |
| Malware download | Quarantine by default; ClamAV worker promotes clean versions only; latest clean version required to download | Live scanner/signature behavior requires Docker and current definitions; archive policy needs further testing |
| Scanner failure | Error remains quarantined and owner can retry | No queue dashboard, backoff, or dead-letter service |
| Stored-file disclosure | AES-GCM encrypted local object bytes and randomized nonces | Key is stored on the same machine; no KMS, rotation, backup, or recovery |
| Prompt injection | Retrieved excerpts are labeled untrusted; model receives no tools; bounded context; citations | A local LLM can still produce misleading answers; retrieval is lexical BM25 |
| Unauthorized content entering RAG | Current owner/share ACL joins happen before ranking/prompt construction | New formats are not extracted; current prototype needs independent penetration testing |
| Sensitive audit leakage | Metadata-only events; current user sees only their own event list | Retention/export/immutability are not yet implemented |
| False anomaly response | Synthetic Isolation Forest findings are review-only and include reasons | Synthetic quality metrics do not predict real detection rates |
| Accidental cloud spend | No cloud SDK or cloud service call in the local app; Terraform reference resources default off; Phase 2 has an estimate gate | Enabling IaC or using any AWS account can incur charges; credits and budgets do not cap spend |
| Browser token theft | Authorization code + PKCE; access token kept in tab sessionStorage and expires per provider | sessionStorage is accessible to same-origin JavaScript; production needs a reviewed server-side session |

## Safe-use rules

- Use only the synthetic Dex identities Alice and Bob, and synthetic files.
- Never log or commit token contents, file text, passwords, encryption keys, or model weights.
- Keep Dex and ClamAV bound to loopback; use the scanner and identity Compose profiles only when needed.
- Keep uploaded object size at or below 10 MiB. Do not use this prototype as a public internet file service.
- Treat the assistant answer as a convenience summary. Check citations and source files before acting on it.
- Do not let anomaly findings automatically suspend accounts, revoke grants, or delete files.
- Before any AWS use, verify credits and service eligibility, prepare a current itemized estimate and guardrails, and get review for the exact deployment. See docs/phase-2-plan.md.
