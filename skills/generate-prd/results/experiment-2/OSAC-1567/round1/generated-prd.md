# Secret Management — Encrypted Storage with Pluggable Backends

| Field       | Value   |
|-------------|---------|
| Author(s)   | Dakota Crowder |
| Jira        | [OSAC-1567](https://issues.redhat.com/browse/OSAC-1567) |
| Date        | 2026-08-12 |

## Problem Statement

Secrets such as cluster kubeconfigs, cluster admin passwords, IdP client secrets, storage credentials, and SSH keys are currently stored as unencrypted fields scattered across resource database tables. This means database access directly exposes sensitive credentials, there is no separation of secret lifecycle from resource lifecycle, no uniform way for users to retrieve secrets, and no ability to rotate encryption keys. Without a dedicated secret management subsystem, OSAC cannot meet basic security expectations for credential storage, and every service that handles secrets must implement its own ad-hoc retrieval pattern (e.g., custom `GetKubeconfig` and `GetAdminPassword` RPCs that internally connect to the Kubernetes hub and know how to locate HyperShift-generated secrets).

This feature addresses secrets across two related use cases that share a common storage and access infrastructure: (1) infrastructure and provider secrets used for operating the cloud, and (2) tenant-facing secrets such as OIDC client secrets, cluster kubeconfigs, cluster admin passwords, and cloud-init credentials. While these use cases serve different audiences, they share the same requirements for encryption at rest, access control, and uniform API access, and are therefore addressed together.

## In Scope

- A dedicated secret resource with full CRUD operations, supporting storage of credentials including but not limited to:
  - **Cluster kubeconfigs** — currently retrieved via a custom `GetKubeconfig` RPC that connects directly to the Kubernetes hub and locates HyperShift-generated secrets; to be replaced by the uniform secret API.
  - **Cluster admin passwords** — currently retrieved via a custom `GetAdminPassword` RPC with the same ad-hoc hub retrieval pattern; to be replaced by the uniform secret API.
  - **IdP/OIDC client secrets** — secrets created by tenant admins for integration with their identity providers.
  - **SSH key pairs** — tenant-managed key pairs for infrastructure access.
  - **Cloud-init secrets** — passwords and credentials embedded in cloud-init configuration for VMs.
  - **Storage credentials** — credentials for accessing storage backends.
- Encryption at rest so that raw database or backend access does not expose secret payloads.
- Integration with an external Vault-compatible secret store (e.g., HashiCorp Vault, OpenBao) as the primary secret backend. The Cloud Service Provider (CSP) is responsible for procuring, deploying, and operating the Vault-compatible secret store; OSAC requires configuration of the store's URL and access credentials.
- Pluggable secret backend architecture so that the system can support additional backend types in the future.
- Secret payloads are excluded from list responses; only individual get requests return the secret data.
- A uniform secret reference model that replaces per-resource ad-hoc retrieval RPCs (e.g., `GetKubeconfig`, `GetAdminPassword`) with a consistent pattern across all services.
- Access control enforcing tenant isolation so that tenants can only access their own secrets.
- The ability to scope OSAC's access privileges to a particular tenant's secrets when operating on behalf of that tenant, limiting the blast radius of any single operation.
- UI support for secret management operations (may be delivered in a follow-on milestone and coordinated separately with UI/UX).

## Out of Scope

- Bundling, productizing, or providing commercial support for any specific secret store implementation — the CSP selects and operates their own Vault-compatible secret store.
- Automated secret rotation — deferred as a future enhancement.
- SSH key cloud-init injection for VMs — VMaaS-specific, tracked in OSAC-51.
- Securing Kubernetes secrets on management clusters — to be addressed as a separate feature.

## User Stories

### Cloud Infrastructure Admin

- As a Cloud Infrastructure Admin, I want secrets encrypted at rest so that database or backend access does not expose sensitive credentials, meeting compliance requirements for tenant secret security.
- As a Cloud Infrastructure Admin, I want to rotate encryption keys without needing to re-encrypt all secrets simultaneously so that key rotation can be performed with minimal disruption.
- As a Cloud Infrastructure Admin, I want to configure the connection to an external Vault-compatible secret store so that I can integrate OSAC with my organization's chosen secret management infrastructure.

### Cloud Provider Admin

- As a Cloud Provider Admin, I want access control policies to enforce tenant isolation for secrets so that tenants cannot access each other's credentials.
- As a Cloud Provider Admin, I want OSAC to limit the scope of its access to only the relevant tenant's secrets when performing operations on behalf of that tenant, so that a compromise in one tenant context does not expose secrets belonging to other tenants.

### Tenant Admin

- As a Tenant Admin, I want to store and manage my OIDC client secrets through a uniform secret API so that I can configure identity provider integration without relying on ad-hoc or per-resource retrieval methods.
- As a Tenant Admin, I want to store and manage SSH key pairs through the uniform secret API so that I can manage infrastructure access credentials in a consistent way.

### Tenant User

- As a Tenant User, I want to retrieve cluster kubeconfigs through the uniform secret API so that I do not depend on a custom `GetKubeconfig` RPC that requires direct hub connectivity and HyperShift-specific knowledge.
- As a Tenant User, I want to retrieve cluster admin passwords through the uniform secret API so that I do not depend on a custom `GetAdminPassword` RPC and have a consistent credential access pattern.
- As a Tenant User, I want to store and retrieve cloud-init secrets (such as VM passwords and credentials) through the uniform secret API so that I can manage VM provisioning credentials alongside other secrets.

## Assumptions

- The existing ad-hoc secret retrieval RPCs (`GetKubeconfig`, `GetAdminPassword`) will be replaced by secret references, and consumers will migrate to the new uniform API.
- The CSP will provide and operate a Vault-compatible secret store (such as HashiCorp Vault or OpenBao) and is responsible for its availability and support.
- The cloud provider admin can use the same secret management infrastructure for provider-level secrets via their own tenant context.

## Dependencies

- **OSAC-1330 (Type-safe resource references):** Provides the SecretReference type that this feature uses to replace ad-hoc secret retrieval RPCs. Must land before or alongside this feature.
- **OSAC-2389 (Per-Project Encryption Key Management):** Extends the encryption key model introduced here with per-project key management. Depends on this feature.
- **External Vault-compatible secret store:** The CSP must deploy and provide OSAC access to a Vault-compatible secret store (e.g., HashiCorp Vault, OpenBao).