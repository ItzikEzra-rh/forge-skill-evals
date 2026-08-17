# Secret Management — Encrypted Storage with Pluggable Backends

| Field       | Value   |
|-------------|---------|
| Author(s)   | Dakota Crowder |
| Jira        | [OSAC-1567](https://issues.redhat.com/browse/OSAC-1567) |
| Date        | 2026-08-10 |

## Problem Statement

Secrets such as cluster kubeconfigs, IdP client secrets, storage credentials, and SSH keys are stored as unencrypted fields within resource database tables. Database access exposes all sensitive credentials in plain text, with no encryption at rest, no ability to rotate encryption keys, and no separation of secret lifecycle from resource lifecycle. There is no uniform access pattern for secret retrieval; each consuming service must independently implement ad-hoc, resource-specific credential retrieval calls, increasing the cost and risk surface of every new secret type. If unaddressed, any database compromise exposes all tenant credentials, and every new secret type requires bespoke access-control work.

## In Scope

- Dedicated secret resource with full CRUD operations and envelope encryption (a wrapping key protects per-secret data keys) for database-backed secrets
- A `SecretClass` resource type that defines and configures available secret backends (database, hub/Kubernetes), allowing administrators to select and configure storage strategies independently of individual secrets
- Pluggable secret backends — administrators can choose between database storage and on-demand retrieval from Kubernetes clusters (hub secret backend)
- Uniform secret retrieval replacing ad-hoc per-resource retrieval operations, using typed secret references
- Secret payloads are excluded from list responses and returned only on individual get requests
- Access control and tenant isolation for secrets via OPA policies
- CLI support for encryption key configuration

## Out of Scope

- External secret manager integration (e.g., HashiCorp Vault) — deferred to a future enhancement
- Automated secret rotation — deferred to a future enhancement
- SSH key cloud-init injection for VMs — VMaaS-specific, tracked separately in OSAC-51
- Per-project encryption key management — tracked in [OSAC-2389](https://issues.redhat.com/browse/OSAC-2389)

## User Stories

### Cloud Infrastructure Admin

- As a Cloud Infrastructure Admin, I want secrets encrypted at rest so that database access alone does not expose sensitive credentials.
- As a Cloud Infrastructure Admin, I want to rotate encryption keys without requiring all existing secrets to be re-encrypted simultaneously so that key rotation does not cause downtime or data-access disruption.
- As a Cloud Infrastructure Admin, I want to configure encryption keys via CLI flags so that I can set up and manage encryption as part of platform deployment.
- As a Cloud Infrastructure Admin, I want to select between database-backed storage and hub (Kubernetes) secret backends via a `SecretClass` configuration so that I can match the secret storage strategy to my infrastructure requirements.

### Tenant Admin

- As a Tenant Admin, I want to create, update, and delete secrets scoped to my organization — including IdP client secrets and storage credentials — through a dedicated secrets API so that sensitive credentials have a consistent, auditable lifecycle separate from the resources that consume them.
- As a Tenant Admin, I want access to secrets strictly scoped to my organization so that credentials I store cannot be read by users in other tenants.

### Tenant User

- As a Tenant User, I want to retrieve cluster kubeconfigs and passwords through a uniform secrets API instead of resource-specific credential retrieval calls so that I have a single, consistent way to access credentials across all services.

## Assumptions

- Envelope encryption and `SecretClass`-based backend selection are sufficient for the current customer requirements; external secret manager integration is not needed in this iteration.
- The hub secret backend can retrieve secrets on-demand from Kubernetes clusters without requiring changes to the hub cluster configuration beyond what OSAC-1330 provides.

## Dependencies

- **OSAC-1330 — Type-safe resource references:** Provides the `SecretReference` type used to replace ad-hoc secret retrieval operations. Must land before or alongside this feature.
- **OSAC-1337 — Implementation epic:** Tracks the work breakdown for this feature; no PRD-level dependency, referenced here for traceability.