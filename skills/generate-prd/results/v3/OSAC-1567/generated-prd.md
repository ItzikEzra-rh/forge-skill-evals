# Secret Management — Encrypted Storage with Pluggable Backends

| Field       | Value   |
|-------------|---------|
| Author(s)   | Dakota Crowder |
| Jira        | [OSAC-1567](https://issues.redhat.com/browse/OSAC-1567) |
| Date        | 2026-08-10 |

## Problem Statement

Secrets such as cluster kubeconfigs, IdP client secrets, storage credentials, and SSH keys are stored as unencrypted fields within resource database tables. Database access exposes all sensitive credentials in plain text, with no encryption at rest, no ability to rotate encryption keys, and no separation of secret lifecycle from resource lifecycle. Retrieving secrets requires ad-hoc, per-resource RPCs (e.g., GetKubeconfig, GetPassword) with no uniform access pattern, forcing every consuming service to implement its own retrieval mechanism. If unaddressed, any database compromise exposes all tenant credentials, and every new secret type requires bespoke API and access-control work.

## In Scope

- Dedicated secret resource with full CRUD operations and envelope encryption for secrets stored in the database
- Pluggable secret backends — administrators can choose between database storage and on-demand retrieval from Kubernetes clusters (hub secret backend)
- Uniform secret retrieval replacing ad-hoc per-resource RPCs, using typed secret references
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

### Cloud Provider Admin

- As a Cloud Provider Admin, I want to select between database-backed storage and hub (Kubernetes) secret backends so that I can match the secret storage strategy to my infrastructure requirements.

### Tenant Admin

- As a Tenant Admin, I want to store and manage secrets such as IdP client secrets through a dedicated secrets API so that org configuration credentials have a consistent lifecycle separate from the resources that consume them.

### Tenant User

- As a Tenant User, I want to retrieve cluster kubeconfigs and passwords through a uniform secrets API instead of per-resource RPCs so that I have a single, consistent way to access credentials across all services.

## Dependencies

- **OSAC-1330 — Type-safe resource references:** Provides the SecretReference type used to replace ad-hoc secret retrieval RPCs. Must land before or alongside this feature.
