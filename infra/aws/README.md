# AWS reference blueprint

This Terraform configuration is a **design artifact** for CloudVault's future AWS mapping. It provisions nothing by default and is not required for the local project. The application currently runs against SQLite, encrypted local files, local Dex, local ClamAV, and local Ollama/mock inference; this blueprint does not convert those adapters into AWS integrations.

## Safety defaults

- `enable_resources` defaults to `false`, so the default plan contains no AWS resources.
- All billable or account-changing use remains out of scope until the current credit balance and eligibility, exact regional estimate (including tax/FX), alerts, quotas, and teardown plan are reviewed together.
- Do not change the flag or run `terraform apply` as part of local development. A Terraform plan is not a price guarantee.
- Optional Cognito and GuardDuty resources are independently disabled by default. GuardDuty, KMS, logging, network, compute, database, model inference, and data transfer are not included in this small foundation.

## What the blueprint models

- Separate S3 quarantine and clean buckets with public access blocked, TLS-only bucket policies, server-side encryption, short expiration, and incomplete multipart-upload cleanup.
- An SQS scan queue and dead-letter queue with bounded retention and retries.
- A short-retention CloudWatch log group.
- Optional Cognito user pool/app client and optional GuardDuty detector, both off by default.

The API, web hosting, scanner compute, PostgreSQL metadata store, KMS key lifecycle, CloudTrail trail, budget notifications, and network topology still need a separately reviewed design and estimate before any cloud deployment. The file-storage and queue resources shown here are foundational examples, not a complete deployed CloudVault service.

## Inputs and review

The Region defaults to `us-east-1` only as a comparison setting; it is not an approved residency or deployment choice. Set unique bucket names only after a formal deployment review. Terraform providers are declared but are not installed or downloaded by this repository.

Before any future cloud milestone, refresh the account facts in `docs/phase-2-plan.md`, prepare a current AWS Pricing Calculator estimate, verify service eligibility against the actual credits, add and test a notification destination, and review the exact resource changes and teardown. Credits and budgets do not enforce a hard spend cap.
