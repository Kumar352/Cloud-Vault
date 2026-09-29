# CloudVault 2.0

CloudVault is a local-first portfolio project for secure file collaboration, malware quarantine and scanning, auditable access, a permission-aware RAG assistant, and explainable ML anomaly detection.

## Project status

Phase 1A foundation is in progress. The first target is a local development environment. AWS architecture and Terraform are for learning and documentation; **nothing is deployed by default**. Any later action that could incur charges requires a service-by-service estimate and your explicit approval.

## Planned capabilities

- Secure file upload, versioning, access control, and collaboration.
- Quarantine and malware scan lifecycle; only clean, authorized files can be downloaded.
- Structured audit events and cloud threat-detection integration in the AWS target design.
- RAG over files the signed-in user is authorized to access, with citations.
- A real local model through Ollama where the host can run it; the model provider will be configurable.
- A separate, explainable anomaly detector trained and evaluated with synthetic audit events first.

## Local development

Prerequisites and exact supported versions will be recorded as the stack is implemented. The planned local services are PostgreSQL with pgvector, MinIO, a local queue/worker, ClamAV, and an optional Ollama model. AWS, Vercel, and hosted model calls stay off unless separately approved.

See [the architecture notes](docs/architecture.md), [the threat model](docs/threat-model.md), and [the development notes](docs/development.md).

## Security and data

Use synthetic files and users during development. Never commit credentials, model weights, real user files, or generated secrets. Treat uploaded content and extracted text as untrusted. Do not log file contents, authentication tokens, or secrets.

## License

License choice is pending owner review. Until a license is selected, do not assume the project is available for reuse.
