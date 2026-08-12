# Secret Management — Encrypted Storage with Pluggable Backends

| Field       | Value   |
|-------------|---------|
| Author(s)   | Dakota Crowder |
| Jira        | [OSAC-1567](https://issues.redhat.com/browse/OSAC-1567) |
| Date        | 2026-08-12 |

## Problem Statement

Secrets such as cluster kubeconfigs, IdP client secrets, storage credentials, and SSH keys are currently stored as unencrypted fields scattered across resource database tables. This means database access directly exposes sensitive credentials, there is no separation of secret lifecycle from resource lifecycle, no uniform way for users to retrieve secrets, and no ability to rotate encryption keys. Without a dedicated secret management subsystem, OSAC cannot meet basic security expectations for credential storage, and every service that handles secrets must implement its own ad-hoc retrieval pattern.

## In Scope

- A dedicated secret resource with full CRUD operations, supporting storage of credentials such as kubeconfigs, IdP client secrets, storage credentials, and SSH keys.
- Encryption at rest for database-backed secrets so that raw database access does not expose secret payloads.
- Pluggable secret backends, allowing admins to choose between database storage and hub/Kubernetes-based on-demand secret retrieval.
- Secret payloads are excluded from list responses; only individual get requests return the secret data.
- A uniform secret reference model that replaces per-resource ad-hoc retrieval (e.g., GetKubeconfig, GetPassword) with a consistent pattern across all services.
- OPA-based access control enforcing tenant isolation so that tenants can only access their own secrets.
- CLI configuration for encryption key settings.

## Out of Scope

- External secret manager integration (e.g., HashiCorp Vault) — deferred as a future enhancement.
- Automated secret rotation — deferred as a future enhancement.
- SSH key cloud-init injection for VMs — VMaaS-specific, tracked in OSAC-51.

## User Stories

### Cloud Infrastructure Admin

- As a Cloud Infrastructure Admin, I want secrets encrypted at rest so that database access does not expose sensitive credentials.
- As a Cloud Infrastructure Admin, I want to rotate encryption keys without needing to re-encrypt all secrets simultaneously so that key rotation can be performed with minimal disruption.
- As a Cloud Infrastructure Admin, I want to configure encryption key settings via CLI flags so that I can set up and manage the encryption configuration for the platform.
- As a Cloud Infrastructure Admin, I want to configure pluggable secret backends so that I can choose between database storage and hub/Kubernetes-based secret retrieval based on my infrastructure requirements.

### Cloud Provider Admin

- As a Cloud Provider Admin, I want OPA policies to enforce tenant isolation for secrets so that tenants cannot access each other's credentials.

### Tenant Admin

- As a Tenant Admin, I want to store and manage secrets such as IdP client secrets through a uniform API so that I do not need to use different per-resource retrieval methods for each secret type.

### Tenant User

- As a Tenant User, I want to retrieve secrets such as cluster kubeconfigs and passwords through a uniform API so that I have a single, consistent way to access credentials instead of per-resource RPCs.

## Assumptions

- The existing ad-hoc secret retrieval RPCs (GetKubeconfig, GetPassword) will be replaced by secret references, and consumers will migrate to the new uniform API.

## Dependencies

- **OSAC-1330 (Type-safe resource references):** Provides the SecretReference type that this feature uses to replace ad-hoc secret retrieval RPCs. Must land before or alongside this feature.
- **OSAC-2389 (Per-Project Encryption Key Management):** Extends the encryption key model introduced here with per-project key management. Depends on this feature.
