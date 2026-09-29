# CloudVault threat model (initial)

## Assets

- User identity, session tokens, sharing grants, and access-control metadata.
- Uploaded files, file versions, extracted text, embeddings, and scan results.
- Audit events, anomaly findings, model prompts, and generated answers.
- Application secrets, encryption keys, and infrastructure configuration.

## Trust boundaries

- Browser to API.
- User/tenant boundary within the API and database.
- Staging/quarantine versus clean object storage.
- Scanner worker and file parsers processing hostile content.
- Retrieved document text entering the language model context.
- Local development environment versus optional AWS deployment.

## Initial threats and controls

| Threat | Initial control |
|---|---|
| Cross-user or cross-tenant access | Resource-level authorization on every operation; negative isolation checks. |
| Malicious upload or archive bomb | Quarantine first, unprivileged isolated scanner, size/time/expansion limits, no download before clean. |
| Prompt injection in a document | Treat document text as untrusted; no tool execution from retrieved content; enforce ACLs before retrieval. |
| Secret or personal-data leakage | Synthetic data by default; exclude secrets/content from logs and Git; restrict model context. |
| Stale/revoked sharing grant | Re-check current ACL on every access and retrieval; short-lived links. |
| False anomaly alert | Human review only; explain findings and report evaluation metrics. |
| Accidental cloud spend | AWS resources off by default; estimate and explicit approval gate; teardown and billing review. |

This is an initial portfolio threat model, not a security certification. Update it as implementation details and abuse cases become concrete.
