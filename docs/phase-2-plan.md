# Phase 2: one-user cloud readiness and cost gate

## Outcome

Phase 2 prepares a secure, short-lived AWS learning demonstration. It does not create resources. The portfolio can meet its main goal with the local application, documentation, diagrams, and source in Git; AWS is an optional comparison exercise and must never be left running just to keep the project available.

The approved operating assumption from the project conversation is one operator account, synthetic content, a single walkthrough, local Ollama or mock RAG, and teardown immediately after the walkthrough. Do not use real files or invite public users.

## Current readiness

- Local implementation and guardrails are described in `phase-1-completion.md` and `development.md`.
- AWS service mapping is in `architecture.md`.
- A disabled-by-default Terraform reference blueprint is in `infra/aws/`; it models a small subset of storage, queue, logs, and optional identity/threat detection. It is not a deployable application and no provider was initialized. A read-only account review on 2026-10-05 found the returned promotional credit records had already expired, so planned AWS usage must be budgeted as out-of-pocket. The existing monthly budget is over its threshold and has no notification subscriber; it is not a working alert. Existing billable resources were found but their ownership/purpose is not confirmed, so they must not be treated as CloudVault demo resources or changed as part of this project. Detailed amounts and resource inventory are kept in the local ignored `data/account-readiness-private.md`, not in public portfolio materials.
- The account is not ready for any CloudVault deployment until existing spending is understood, an effective notification path is in place, and the user reviews the exact current-region estimate. The Phase 2 decision can remain “local portfolio only”; a cloud deployment is optional.
- Public AWS credit offers are not evidence that this account has credits or that a proposed service is eligible. Do not subtract credits in an estimate until the account's billing console confirms the amount, expiry, and eligible services.
- No deployment or account mutation is part of this phase's repository work. Terraform resources remain disabled by default.

## Recommended route

1. Finish and review the local portfolio artifact first. A cloud deployment is not required to publish the source or document the intended architecture.
2. If a live cloud walkthrough is later useful, use a single region and a time-boxed, one-user demo. Choose the region only after reviewing data location, latency, and current region-specific prices.
3. Keep the model local. Keep anomaly detection as the local review-only model. Do not call Bedrock or any hosted model for this milestone.
4. Prefer services that can be fully deleted after the session. Avoid always-on RDS, NAT Gateway, load balancers, public IPv4, multi-AZ, and idle containers. If the demo must use managed PostgreSQL, include its full running hours and storage/backup charges; stopping it does not remove every associated charge, and RDS stop behavior has time limits.
5. Use one synthetic account if possible; use local Dex for the existing second-person sharing walkthrough. Keep the full security story documented even when a managed service is omitted from a zero-cost demo.

## Cost envelope for decision-making

These figures are deliberately envelopes, not a quote or a claim of zero cost. The original code is local-first and the AWS resources are optional. All amounts below are USD before tax and INR planning conversions. For conversion only, use ₹90 per USD as a rounded planning assumption (not a current RBI rate or card settlement rate); recalculate using the rate on the date of any estimate review. Add an illustrative 18% GST only if AWS billing tax treatment for this account confirms it applies; tax, FX spread, and issuer fees are not included in the base figures.

| Route | Planning ceiling for a single 8-hour demo | INR at ₹90/USD, before tax | What it means |
|---|---:|---:|---|
| Local portfolio only | $0 cloud | ₹0 | Recommended default: existing workstation, local Dex, ClamAV, SQLite/files, Ollama/mock. Internet/electricity and already-owned hardware excluded. |
| Cloud proof, no managed database or network gateway | $5–$25 | ₹450–₹2,250 | Static UI plus small API/worker, bounded S3/SQS/logging/identity/key operations and a single short session; strict usage limits and teardown. This is only an early envelope; actual region, API shape, scanner runtime, log volume, transfer and security telemetry can change it. |
| Cloud proof with managed PostgreSQL or richer security telemetry | $15–$60+ | ₹1,350–₹5,400+ | Adds hours of database compute/storage/backups or paid telemetry/data events. The `+` is intentional; network gateways or expanded GuardDuty/log sources can exceed this range. |
| Always-on monthly deployment | Not recommended; quote separately | Not estimated | Idle compute, database, addresses, gateways, logs, security data sources and backups can continue to bill. Do not use an always-on environment for this portfolio. |

The eight-hour estimates assume: one region; one authenticated operator; at most 20 synthetic objects; a 10 MiB per-object cap and 50 MiB total; at most 1 GiB of temporary object storage including versions; no public internet egress beyond one small walkthrough; at most 100 API requests; at most 100 scan attempts over no more than 2 hours; no hosted LLM; 1 GiB maximum retained logs with short retention; no NAT Gateway, load balancer, static IP, multi-AZ, data-event trail, or continuous GuardDuty plan unless added as a separately priced item. This is a budgeting envelope only, not validated AWS Calculator output. Set an estimate of `$0` to show whether the solution can remain local; that is the zero-cost result.

To plan tax sensitivity only: if 18% GST were confirmed applicable, the illustrative taxed amounts would be $5.90–$29.50 (₹531–₹2,655) and $17.70–$70.80 (₹1,593–₹6,372). AWS tax is account/address and billing-specific; verify with AWS billing before relying on this illustration.

### Cost drivers and pricing references

AWS prices vary by region, configuration, and usage. The official pricing pages below are live references, not a substitute for an AWS Pricing Calculator estimate for the selected region.

| Service family | What can cost money | Design limit for a one-user proof |
|---|---|---|
| Lambda/API Gateway | Request count, function memory/runtime, gateway type, data transfer, and VPC use | Set a hard request budget, short timeouts, no provisioned concurrency, no VPC attachment unless the estimate includes networking. [Lambda pricing](https://aws.amazon.com/lambda/pricing/) · [API Gateway pricing](https://aws.amazon.com/api-gateway/pricing/) |
| RDS PostgreSQL | Instance-hours, storage, backups, I/O and network; stopping an instance is not equivalent to deleting every billed artifact | Avoid in the zero-cost path. If included, specify instance class, storage, backup retention, start/stop window, and final deletion. [RDS PostgreSQL pricing](https://aws.amazon.com/rds/postgresql/pricing/) |
| S3 and transfer | Stored bytes/versions, request classes, retrieval, lifecycle and outbound transfer | Maximum 1 GiB temporary data, no replication, short lifecycle, explicit empty-bucket teardown. [S3 pricing](https://aws.amazon.com/s3/pricing/) |
| Queue and scan worker | SQS requests plus worker vCPU/memory/runtime and image storage | Queue max 25, file cap 10 MiB, max 100 scans / 2 hours, max 2 retries, dead-letter cap and deletion. [SQS pricing](https://aws.amazon.com/sqs/pricing/) · [Fargate pricing](https://aws.amazon.com/fargate/pricing/) |
| Identity | Monthly active users, feature tier, federation, MFA SMS/email and advanced security | One synthetic test account; prefer no SMS or email OTP for the proof; verify user-pool tier and account's free/credit eligibility. [Cognito pricing](https://aws.amazon.com/cognito/pricing/) |
| Logs/audit/threat detection | Log ingestion/retention, CloudTrail data events, GuardDuty data sources/features, notifications | 1 GiB log ingestion ceiling; 7-day retention; management events only unless separately reviewed; do not turn on optional threat-data plans without a quote. [CloudWatch pricing](https://aws.amazon.com/cloudwatch/pricing/) · [CloudTrail pricing](https://aws.amazon.com/cloudtrail/pricing/) · [GuardDuty pricing](https://aws.amazon.com/guardduty/pricing/) |
| Key/config | KMS key-month, API requests, secrets/config storage and retrieval | Avoid creating keys/secrets until the exact month and request count are estimated; include deletion schedule and recovery considerations. [KMS pricing](https://aws.amazon.com/kms/pricing/) · [Secrets Manager pricing](https://aws.amazon.com/secrets-manager/pricing/) |
| AI | Bedrock input/output token cost plus any knowledge-base/vector services | No hosted AI in this milestone. Local Ollama/mock has no provider usage charge. [Bedrock pricing](https://aws.amazon.com/bedrock/pricing/) |
| Budget alerts | AWS Budgets without actions are currently documented as free; alert email and billing delay still matter | Use cost and forecast thresholds. Alerts are warnings, not a spending cap and not instantaneous. Do not configure budget actions without separate review. [AWS Budgets FAQ](https://aws.amazon.com/aws-cost-management/aws-budgets/faqs/) |

AWS's currently published new-customer offer says up to $200 of credits may be available for eligible accounts/services; it is time-bound and account-specific. Treat it as $0 until the signed-in billing console shows usable balance and eligibility. Credits do not prevent spending beyond the balance, may exclude services, and may expire. [AWS S3 pricing/free-tier notes](https://aws.amazon.com/s3/pricing/)

## Mandatory pre-deployment evidence

Before any creation, start, enablement, or paid service call, prepare and review all of the following together:

- Signed-in account ID and selected Region, without exposing access keys.
- Live credit balance, expiration, service eligibility, account plan, and billing tax country.
- Calculator export or saved estimate with exact resources, Region, quantities, runtime, storage, retention, and transfer assumptions.
- Estimate with credits set to zero, plus a separate eligible-credit view; include tax and card/FX sensitivity.
- Planned maximum exposure in USD and INR, and a statement of what might not be credit-covered.
- Existing budgets/alerts and the proposed threshold alerts; confirm whether they notify only or can stop resources.
- Service quotas and application caps for upload, object count, scanning, log intake/retention, requests and AI tokens.
- Teardown commands and a post-teardown inventory/billing review. Document eventual-consistency and delayed billing limitations.

Show this exact estimate for owner review before any deployment or operation that could incur charges. If account data or billing controls cannot be verified, remain local. Credits and alerts are not hard spending guarantees.

## Usage guardrails for any later proof

- One synthetic operator; local Dex is the preferred identity provider for the no-cost demo.
- No real documents, public registration, or open upload endpoint.
- At most 20 objects, 10 MiB each, 50 MiB combined; no versioning beyond the smallest demonstrative case.
- At most 100 scan submissions in a two-hour window, 2 retries, hard worker timeout and bounded dead-letter queue.
- At most 100 API requests, bounded payloads and explicit throttles.
- Logs: metadata only, no document text/tokens/secrets; cap 1 GiB and expire in 7 days.
- AI: local Qwen model or grounded mock; hosted model disabled.
- After walkthrough: stop or delete compute; empty/delete buckets and queues; delete database and snapshots; remove keys/secrets only after securely handling encrypted data; verify no gateways, addresses, disks, logs, trails, detection plans, or backups remain; check billing after usage records settle.

## Phase 2 exit criteria

Phase 2 source and planning work is complete for the portfolio scope: architecture mapping, broad planning envelope, cost drivers, usage caps, teardown guidance, and a disabled-by-default IaC reference are documented. The account-specific readiness gate is **not clear to proceed**: expired credits, a budget alert with no subscriber, active account spend, and unrelated resources with unknown ownership require resolution. Do not deploy until the account gate is satisfied and the exact estimate is reviewed. It is valid for the final decision to be “no AWS deployment; local portfolio is enough.”
