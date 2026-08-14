---

```yaml
---
title: secret-management
authors:
  - TBD
creation-date: 2026-08-13
last-updated: 2026-08-13
tracking-link:
  - https://redhat.atlassian.net/browse/OSAC-1567
prd:
  - "prd.md"
see-also: []
replaces: []
superseded-by: []
---
```

# Secret Management

## Summary

This enhancement introduces a `Secret` resource in `fulfillment-service` backed by a pluggable Vault-compatible secret store, enabling encrypted at-rest storage, tenant-scoped isolation, and a uniform CRUD API for all OSAC credential types. See [PRD](prd.md) for detailed requirements.

## Motivation

OSAC services currently store credentials — cluster kubeconfigs, SSH keys, OIDC client secrets, storage credentials — as plaintext fields embedded directly in the owning resource's database row. This conflates credential lifecycle with resource lifecycle, prevents independent credential rotation, and violates data-at-rest encryption requirements that Cloud Infrastructure Admins must meet. Tenant users must learn resource-specific retrieval paths for each credential type, and there is no cross-resource inventory of what credentials exist within a tenant.

The design introduces a first-class `Secret` resource that stores its payload exclusively in an external, Vault-compatible secret store (HashiCorp Vault, OpenBao, or equivalent). `fulfillment-service` holds only metadata and a backend reference; the encrypted payload never touches the OSAC PostgreSQL database. All OSAC services (BMaaS, CaaS, VMaaS, MaaS, Enclave) converge on this single API for creating, retrieving, and referencing credentials. [PRD: Problem Statement]

### Goals

- Introduce a single `Secret` resource with standard CRUD via the fulfillment-service gRPC/REST API.
- Store encrypted payloads exclusively in the Vault-compatible backend; keep only opaque references in PostgreSQL. [PRD: In Scope]
- Support pluggable backend implementations so cloud providers can supply a Vault-compatible store of their choosing. [PRD: In Scope]
- Enforce tenant-scoped isolation at the Vault path level so OSAC never reads across tenant boundaries. [PRD: In Scope]
- Support automatic `Secret` creation during resource provisioning (e.g., kubeconfig written at cluster-ready time). [PRD: In Scope]
- Reuse the existing controller reconciliation pattern (`provisioning.RunProvisioningLifecycle`), RBAC annotation conventions, and OPA policy shape already established for other OSAC resources.
- Cover all four OSAC personas in RBAC rules.

### Non-Goals

- Secret rotation automation — users may call `UpdateSecret` to replace a payload, but scheduled or trigger-based rotation workflows are deferred. [PRD: Out of Scope]
- UI — secret management is API and CLI only for OSAC 0.2; no `osac-ux` changes in this EP. [PRD: Out of Scope]
- Vault deployment or lifecycle management — cloud providers are responsible for operating the secret store. [PRD: Out of Scope / Dependencies]
- Cross-tenant secret sharing.
- Secret versioning or history (Vault versions are an implementation detail, not exposed through the OSAC API).

## Proposal

Three components are modified or extended:

1. **`fulfillment-service`** — adds the `Secret` proto resource, gRPC service methods, database table (metadata only), and Vault backend adapter interface.
2. **`osac-operator`** — adds a `Secret` controller that writes system-generated secrets (e.g., kubeconfigs) into the backend via the fulfillment-service API after resource provisioning completes.
3. **`osac-aap`** — no new playbooks required; the operator calls the fulfillment-service API directly. [Assumption]

The PostgreSQL `secrets` table stores only the `Secret` resource metadata (id, tenant, name, type, backend reference path, conditions). The actual payload bytes are stored under a per-tenant path hierarchy in Vault (`osac/<tenant-id>/secrets/<secret-id>`), encrypted by Vault's transit engine. [PRD: In Scope]

A `SecretBackend` interface in Go is introduced in `fulfillment-service`, with a Vault adapter as the first implementation. Future adapters (AWS Secrets Manager, Azure Key Vault) can be registered without API changes. [PRD: In Scope — pluggable backends]

### Workflow Description

#### Workflow 1 — Tenant User creates a self-service secret

**Starting state:** Tenant User is authenticated; tenant already exists.

1. Tenant User calls `CreateSecret` with `spec.type = SSH_KEY`, `spec.display_name`, and `spec.payload` (base64-encoded private key).
2. `fulfillment-service` validates the request (type is a known enum value; payload is non-empty; name is unique within the tenant).
3. fulfillment-service writes the encrypted payload to Vault at path `osac/<tenant-id>/secrets/<new-secret-id>` using the tenant-scoped Vault token. [PRD: In Scope — tenant-scoped privilege isolation]
4. fulfillment-service creates a `secrets` database row with the backend path and initial condition `SecretReady=True`.
5. Response returns the `Secret` resource with **`status.conditions`** set; `spec.payload` is **omitted** from the response.
6. Tenant User can now reference the `Secret` by `id` in other resource specs (e.g., `ComputeInstanceSpec.ssh_key_secret_id`).

#### Workflow 2 — Tenant User retrieves a secret payload

**Starting state:** Secret exists; Tenant User has `secrets:read-payload` permission.

1. Tenant User calls `GetSecret` with `{id}` and query parameter `include_payload=true`.
2. fulfillment-service reads the Vault path from the `secrets` row, fetches the payload from Vault, and returns `spec.payload` populated in the response.
3. If `include_payload=false` (default), the payload field is suppressed; only metadata is returned. [PRD: User Story — list secrets without exposing data]

```
Tenant User ──CreateSecret(payload)──► fulfillment-service ──write──► Vault
                                            │
                                         DB row (metadata + vault path)
                                            │
Tenant User ◄──Secret{id, conditions}───────┘

Tenant User ──GetSecret(id, include_payload=true)──► fulfillment-service ──read──► Vault
Tenant User ◄──Secret{id, payload}──────────────────────────────────────────────────┘
```

#### Workflow 3 — Automatic secret creation during resource provisioning

**Starting state:** A `ClusterOrder` (or other resource) has just reached `Provisioned` state; the provisioning job has written the kubeconfig to the management cluster.

1. `osac-operator` `Secret` controller detects the provisioning completion event.
2. Controller calls `CreateSecret` on behalf of the resource owner with `spec.type = KUBECONFIG`, `spec.owner_reference = <ClusterOrder id>`, and the retrieved kubeconfig bytes as payload.
3. fulfillment-service stores the payload in Vault and writes the metadata row.
4. Controller patches the owning resource's status with `status.kubeconfig_secret_id = <new-secret-id>`.
5. Tenant User retrieves the kubeconfig via `GetSecret(id, include_payload=true)` — identical to any other secret. [PRD: User Story — credential access consistent regardless of how the secret was created]

#### Workflow 4 — Tenant User deletes a secret

1. Tenant User calls `DeleteSecret(id)`.
2. fulfillment-service checks whether any resource references this secret via `owner_reference` or foreign-key lookup. If in use, returns `FAILED_PRECONDITION` (equivalent of Z0003 — resource in use). [PRD: User Story — delete a secret]
3. fulfillment-service calls Vault to delete (destroy) the secret version at `osac/<tenant-id>/secrets/<secret-id>`.
4. fulfillment-service removes the database row.
5. Response: empty (204 equivalent at REST layer).

#### Error Flows

| Situation | gRPC Code | Detail |
|-----------|-----------|--------|
| Payload empty on create | `INVALID_ARGUMENT` | `"spec.payload must not be empty"` |
| Unknown `spec.type` | `INVALID_ARGUMENT` | `"spec.type is not a recognized SecretType"` |
| Name collision within tenant | `ALREADY_EXISTS` | `"a secret with this name already exists in the tenant"` |
| Secret not found | `NOT_FOUND` | `"secret {id} not found"` |
| Caller lacks read-payload permission | `PERMISSION_DENIED` | `"caller does not have secrets:read-payload"` |
| Secret in use on delete | `FAILED_PRECONDITION` | `"secret {id} is referenced by {resource-type} {resource-id}"` |
| Vault unreachable on write | `UNAVAILABLE` | retried by controller; exposed as condition `SecretReady=False, reason=VaultUnavailable` |
| Concurrent update conflict | `ABORTED` | `"resource version conflict; retry the operation"` |

### API Extensions

A new `Secret` proto resource and `SecretService` gRPC service are added to `fulfillment-service`. No Kubernetes CRDs or admission webhooks are introduced; the `Secret` resource is a fulfillment-service API resource only.

A new `secrets` PostgreSQL table is added (schema in [Implementation Details](#implementationdetailsnotesconstraints)).

No existing resource schemas are modified in this EP. Existing resources that hold raw credential fields (e.g., `ClusterOrder.kubeconfig`) will be migrated to reference `Secret.id` in a follow-on EP. [Assumption — migration deferred]

## UX Alignment

Secret management is CLI and API only for OSAC 0.2; no `osac-ux` TypeScript API files exist for this resource. [PRD: Out of Scope — UI]

This section is N/A — no `@temp-api` file exists for `Secret` at this time.

## Implementation Details/Notes/Constraints

### Proto Schema

```protobuf
syntax = "proto3";
package osac.fulfillment.v1;

import "google/api/annotations.proto";
import "google/protobuf/timestamp.proto";
import "osac/fulfillment/v1/meta.proto";

// SecretType enumerates the kinds of credentials OSAC manages.
enum SecretType {
  SECRET_TYPE_UNSPECIFIED = 0;
  SECRET_TYPE_SSH_KEY     = 1;
  SECRET_TYPE_KUBECONFIG  = 2;
  SECRET_TYPE_OIDC_CLIENT = 3;
  SECRET_TYPE_CLOUD_INIT  = 4;
  SECRET_TYPE_STORAGE     = 5;
  SECRET_TYPE_GENERIC     = 6;
}

message Secret {
  string   id       = 1;
  Metadata metadata = 2;
  SecretSpec   spec   = 3;
  SecretStatus status = 4;
}

message SecretSpec {
  // Human-readable label. Must be unique within the tenant.
  string display_name = 1;

  // Type determines validation and downstream consumer behaviour.
  SecretType type = 2;

  // payload holds the raw secret bytes (base64-encoded in JSON transcoding).
  // On responses, this field is omitted unless include_payload=true is requested.
  // [PRD: User Story — list secrets without exposing data]
  bytes payload = 3;

  // owner_reference links system-created secrets to their originating resource.
  // Set by the operator; omitted for self-service secrets.
  string owner_reference = 4;
}

message SecretStatus {
  repeated Condition conditions = 1;
  // vault_path is the backend path where the payload is stored.
  // Exposed in status for auditability; payload is NOT included.
  string vault_path = 2;
}

// SecretService exposes CRUD for the Secret resource.
service SecretService {
  rpc CreateSecret(CreateSecretRequest) returns (Secret) {
    option (google.api.http) = {
      post: "/v1/tenants/{tenant_id}/secrets"
      body: "*"
    };
  }

  rpc GetSecret(GetSecretRequest) returns (Secret) {
    option (google.api.http) = {
      get: "/v1/tenants/{tenant_id}/secrets/{id}"
    };
  }

  rpc ListSecrets(ListSecretsRequest) returns (ListSecretsResponse) {
    option (google.api.http) = {
      get: "/v1/tenants/{tenant_id}/secrets"
    };
  }

  rpc UpdateSecret(UpdateSecretRequest) returns (Secret) {
    option (google.api.http) = {
      patch: "/v1/tenants/{tenant_id}/secrets/{id}"
      body: "*"
    };
  }

  rpc DeleteSecret(DeleteSecretRequest) returns (google.protobuf.Empty) {
    option (google.api.http) = {
      delete: "/v1/tenants/{tenant_id}/secrets/{id}"
    };
  }
}

message CreateSecretRequest {
  string tenant_id = 1;
  Secret secret    = 2;
}

message GetSecretRequest {
  string tenant_id       = 1;
  string id              = 2;
  bool   include_payload = 3;
}

message ListSecretsRequest {
  string tenant_id  = 1;
  string page_token = 2;
  int32  page_size  = 3;
  // Optional filter by type.
  SecretType type_filter = 4;
}

message ListSecretsResponse {
  repeated Secret secrets        = 1;
  string          next_page_token = 2;
}

message UpdateSecretRequest {
  string tenant_id = 1;
  string id        = 2;
  // Only spec.payload and spec.display_name are mutable.
  Secret secret    = 3;
}

message DeleteSecretRequest {
  string tenant_id = 1;
  string id        = 2;
}
```

### Database Schema

```sql
CREATE TABLE secrets (
  id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id       UUID        NOT NULL REFERENCES tenants(id),
  display_name    TEXT        NOT NULL,
  type            TEXT        NOT NULL,
  vault_path      TEXT        NOT NULL,
  owner_reference UUID,                          -- nullable; set for system-created secrets
  resource_version BIGINT     NOT NULL DEFAULT 0,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  conditions      JSONB       NOT NULL DEFAULT '[]'
);

CREATE UNIQUE INDEX secrets_tenant_name_uidx
  ON secrets(tenant_id, display_name);

-- Immutable fields: id, tenant_id, type, vault_path (enforce via trigger Z0001)
-- Delete protection: check references before delete (Z0003 logic in application layer)
```

`spec.type` and `vault_path` are immutable after creation (enforced by a PostgreSQL trigger raising SQLSTATE `Z0001`). Attempts to change them are translated to `INVALID_ARGUMENT` by `translateError`. [Codebase: fulfillment-service/internal/db/errors.go]

### Vault Backend Interface

```go
// SecretBackend is the abstraction layer for pluggable secret stores.
// [PRD: In Scope — pluggable secret backends]
type SecretBackend interface {
    // Write stores or overwrites the payload at the given path.
    Write(ctx context.Context, path string, payload []byte) error
    // Read retrieves the payload. Returns (nil, ErrNotFound) if absent.
    Read(ctx context.Context, path string) ([]byte, error)
    // Delete permanently destroys the secret at path.
    Delete(ctx context.Context, path string) error
}
```

The initial implementation (`VaultBackend`) uses HashiCorp/OpenBao KV v2 with the Vault Go SDK. The backend is configured via `fulfillment-service` operator config (mount path, address, token, TLS CA). [Assumption — token-based auth; AppRole or Kubernetes auth methods deferred]

### Vault Path Convention

```
osac/<tenant-id>/secrets/<secret-id>
```

Each tenant's secrets are grouped under their own Vault path prefix. OSAC uses a Vault policy per tenant that scopes its token to only `osac/<tenant-id>/*`, satisfying tenant-scoped privilege isolation. [PRD: In Scope — OSAC limits its access to only a tenant's secrets]

### Payload Handling

- `spec.payload` is never written to PostgreSQL.
- `spec.payload` is omitted from all responses unless `GetSecretRequest.include_payload = true`.
- `ListSecrets` **never** returns payloads, regardless of request flags. [PRD: User Story — list secrets without exposing data]
- Payload bytes are validated to be non-empty on Create and Update.

### CRUD Operation Details

| Operation | Validation | Vault Op | DB Op | Error Codes |
|-----------|-----------|----------|-------|-------------|
| **Create** | type known; payload non-empty; display_name unique | `Write(path, payload)` | `INSERT` | `INVALID_ARGUMENT`, `ALREADY_EXISTS` |
| **Get** | secret belongs to caller's tenant | `Read(path)` if include_payload | `SELECT` | `NOT_FOUND`, `PERMISSION_DENIED` |
| **List** | tenant scoped | none | `SELECT WHERE tenant_id=?` | — |
| **Update** | payload non-empty; display_name unique if changed; type/vault_path immutable | `Write(path, payload)` | `UPDATE` + Z0001 check | `INVALID_ARGUMENT`, `NOT_FOUND`, `ABORTED` |
| **Delete** | no resource references this secret | `Delete(path)` | `DELETE` | `NOT_FOUND`, `FAILED_PRECONDITION` |

### Security Considerations

**Encryption at rest.** Vault's transit engine or KV v2 encryption-as-a-service ensures payloads are encrypted. The OSAC PostgreSQL database never holds the plaintext. [PRD: User Story — Cloud Infrastructure Admin]

**Tenant isolation.** Each tenant has a dedicated Vault policy and token scoped to `osac/<tenant-id>/*`. The fulfillment-service server obtains the tenant-scoped token from a Vault AppRole or Kubernetes auth role (the exact auth method is an `[Open Question]`). OPA policies additionally filter list results to the caller's tenant, enforced at the gRPC interceptor layer consistent with existing resources. [PRD: In Scope — tenant-scoped privilege isolation]

**Payload exposure.** `GetSecret` with `include_payload=true` is an audited operation. Access is gated on the `secrets:read-payload` permission, which is granted only to the secret owner and Tenant Admins by default. [PRD: User Story — Tenant Admin controls RBAC]

**Immutable fields.** `spec.type` and `vault_path` cannot be changed after creation; enforced at DB layer (Z0001). This prevents a caller from re-pointing a secret reference to a different Vault path post-creation.

**Input validation.** `display_name` is validated for length (≤ 255 chars) and printable UTF-8. `payload` must be non-empty bytes. [Assumption — max display_name length]

### Failure Handling and Recovery

| Failure Mode | What Happens | Recovery | User Observes |
|---|---|---|---|
| Vault unreachable on `CreateSecret` | Write to Vault fails; DB row is not created | Server returns `UNAVAILABLE`; client retries | `UNAVAILABLE` gRPC error |
| Vault write succeeds, DB INSERT fails | Vault path written but no DB row | fulfillment-service detects dangling path on next create attempt (same UUID path unlikely); [Assumption — orphan cleanup via periodic reconciler] | `INTERNAL` gRPC error; client should retry; retried create gets new UUID path |
| Vault unreachable on `GetSecret(include_payload=true)` | Metadata retrieved from DB; Vault read fails | Server returns `UNAVAILABLE` | `UNAVAILABLE` gRPC error; metadata visible via `include_payload=false` |
| Vault unreachable on `DeleteSecret` | Vault delete fails; DB row not removed | Returns `UNAVAILABLE`; secret remains intact | `UNAVAILABLE`; secret still visible in list |
| Immutable field update attempted | DB trigger raises Z0001 | `translateError` maps to `INVALID_ARGUMENT` | `INVALID_ARGUMENT: field type is immutable` |
| Secret in use on delete | Application-layer check finds referencing resource | Returns `FAILED_PRECONDITION` | `FAILED_PRECONDITION: secret {id} is referenced by {type} {id}` |
| Concurrent `UpdateSecret` conflict | `resource_version` mismatch detected | Returns `ABORTED` | `ABORTED: resource version conflict; retry` |
| Controller restart mid-creation | Operator re-reconciles; calls `CreateSecret` again with idempotent display_name | `ALREADY_EXISTS` from server; controller reads existing secret instead | No user-visible disruption |
| Vault token expired during operation | Vault SDK returns 403 | `[Assumption]` — fulfillment-service re-authenticates via configured auth method and retries once; returns `UNAVAILABLE` on second failure | `UNAVAILABLE` |

### RBAC / Tenancy

The `Secret` resource participates in the existing annotation-based tenancy model:

| Annotation | Value |
|---|---|
| `osac.openshift.io/tenant` | Tenant ID |
| `osac.openshift.io/owner-reference` | Owner resource ID (for system-created secrets) |

OPA policies enforce that a caller may only operate on `Secret` resources where `osac.openshift.io/tenant` matches their authenticated tenant claim.

**Role permissions:**

| Role | Create | Get (no payload) | Get (payload) | List | Update | Delete |
|---|---|---|---|---|---|---|
| Cloud Infrastructure Admin | ✗ | ✓ | ✗ | ✓ | ✗ | ✗ |
| Cloud Provider Admin | ✗ | ✓ | ✗ | ✓ | ✗ | ✗ |
| Tenant Admin | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Tenant User | ✓ (own secrets) | ✓ | ✓ (own secrets) | ✓ (own) | ✓ (own) | ✓ (own) |

[PRD: User Story — Tenant Admin controls RBAC]

System-created secrets (kubeconfigs, admin passwords) are owned by the provisioning controller and visible to the tenant that owns the parent resource.

### Observability and Monitoring

No new observability changes. Existing monitoring mechanisms apply.

The `vault_path` field in `SecretStatus` provides auditability — operators can cross-reference OSAC secret IDs with Vault audit logs for read/write events. Vault's native audit log is the primary audit trail for payload access.

### Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Vault becomes a single point of failure for all credential access | Cloud providers must deploy Vault in HA configuration; OSAC returns `UNAVAILABLE` gracefully rather than corrupting state |
| Tenant isolation misconfiguration in Vault policies | Integration tests explicitly verify cross-tenant access is denied; OPA policies add a second enforcement layer |
| Payload accidentally logged | gRPC interceptors must scrub `spec.payload` from structured logs; implement a `SecretSpec` log sanitizer [Assumption] |
| Vault path orphans if DB transaction fails | [Open Question 1] — consider two-phase creation or a reconciler that garbage-collects unreferenced Vault paths |
| Operator calling `CreateSecret` on behalf of resource | Operator must authenticate with a service-account Vault token, not a tenant token — token management requires installer configuration [Assumption] |

### Drawbacks

- **Operational dependency.** OSAC now requires an external Vault-compatible store to be healthy for any secret CRUD operation. This increases deployment complexity and operator burden.
- **Partial atomicity.** Vault and PostgreSQL are two separate data stores with no distributed transaction. The implementation must tolerate and recover from split-brain between the two (Vault write succeeds, DB fails). The reconciler approach adds complexity.
- **Backend portability.** The `SecretBackend` interface provides pluggability, but each new adapter requires its own auth, path convention, and error-mapping logic. This is a maintenance burden if multiple backends are adopted in practice.

## Alternatives (Not Implemented)

### Alternative 1 — Encrypt payloads in PostgreSQL using pgcrypto

Encrypt credentials in the existing PostgreSQL database using `pgcrypto` with a per-tenant encryption key. No external dependency required.

**Rejected because:** Encryption keys must be stored somewhere, and if they are also in PostgreSQL the defense-in-depth value is minimal. Cloud providers have expressed a requirement to bring their own secret store, which this approach cannot satisfy. [PRD: In Scope — pluggable secret backends]

### Alternative 2 — Store secrets as Kubernetes Secrets in the management cluster

Leverage the management cluster's `etcd` encryption-at-rest and Kubernetes RBAC to manage credentials as `v1/Secret` objects, with fulfillment-service reading them via the Kubernetes API.

**Rejected because:** This tightly couples `fulfillment-service` to a specific Kubernetes cluster and makes the secret store management cluster-specific, preventing pluggability. Kubernetes RBAC does not map naturally to OSAC's tenant model. [PRD: In Scope — pluggable backends; Assumptions]

### Alternative 3 — Embed payload in `SecretStatus` only, no dedicated payload field in Spec

Treat `GetSecret` with `include_payload=true` as returning the payload in `status.payload` rather than `spec.payload`, keeping `Spec` write-only for caller-supplied input.

**Rejected because:** The standard OSAC object shape has `Spec` = desired state (caller-controlled) and `Status` = observed state (system-controlled). Payload is caller-supplied data; it belongs in `Spec`. The suppression-by-default mechanism (`include_payload` flag) addresses the exposure concern without violating the resource model. [Codebase: OSAC standard object shape]

## Open Questions

1. **Vault path orphan cleanup** — If the DB INSERT fails after a successful Vault write, the payload is orphaned. Should fulfillment-service implement a periodic reconciler to garbage-collect unreferenced Vault paths, or use a Vault lease with a short TTL as a safety net?

2. **Vault auth method** — The design assumes token-based auth as a placeholder. Should the initial implementation use AppRole (simpler, more portable) or Kubernetes auth (native to OSAC deployment model)?

3. **Operator service-account token** — The operator needs a Vault token with write permission to create system-generated secrets on behalf of a tenant. What is the token provisioning model: one token per tenant scoped to `osac/<tenant-id>/*`, or a single operator-wide token with broader scope?

4. **`spec.type` immutability UX** — Is it acceptable that a caller cannot change the type of a secret (e.g., cannot re-classify a `GENERIC` secret as `SSH_KEY`)? Or should type be mutable with appropriate re-validation?

## Test Plan

### Unit Tests

- `SecretSpec` validation rejects empty payload with `INVALID_ARGUMENT`.
- `SecretSpec` validation rejects unknown `type` enum values with `INVALID_ARGUMENT`.
- `translateError` maps DB SQLSTATE `Z0001` to `INVALID_ARGUMENT` for immutable field violations on `type` and `vault_path`.
- `translateError` maps DB SQLSTATE `Z0003` to `FAILED_PRECONDITION` for delete-protection violations.
- `ListSecretsResponse` never includes `spec.payload` regardless of request flags.
- `GetSecret` with `include_payload=false` returns `spec.payload` as nil/empty.
- `VaultBackend.Write` followed by `VaultBackend.Read` returns original bytes (round-trip test with Vault dev server).
- `VaultBackend.Delete` followed by `VaultBackend.Read` returns `ErrNotFound`.
- Concurrent `UpdateSecret` with mismatched `resource_version` returns `ABORTED`.
- Vault path convention generates `osac/<tenant-id>/secrets/<secret-id>` correctly.

### Integration Tests

- `CreateSecret` with valid `SSH_KEY` payload writes to Vault KV v2 and returns a `Secret` with `SecretReady=True` condition; DB row contains correct `vault_path`.
- `GetSecret` without `include_payload=true` does not call Vault (verified by mock/spy).
- `GetSecret` with `include_payload=true` retrieves and returns the correct payload bytes.
- `ListSecrets` returns metadata for all secrets scoped to the caller's tenant and omits secrets of other tenants (cross-tenant isolation check).
- `UpdateSecret` replaces the Vault payload; `resource_version` increments in the DB row.
- `DeleteSecret` for a secret referenced by a `ComputeInstance.ssh_key_secret_id` returns `FAILED_PRECONDITION`.
- `DeleteSecret` for an unreferenced secret removes both the Vault path and the DB row.
- Immutable field update (`spec.type` change via `UpdateSecret`) returns `INVALID_ARGUMENT`.
- System-created secret: operator controller writes a `KUBECONFIG` secret via `CreateSecret`; parent resource status is patched with `kubeconfig_secret_id`.
- Vault unavailable (simulated): `CreateSecret` returns `UNAVAILABLE`; no DB row is inserted.

### E2E Tests

- Tenant User creates an `SSH_KEY` secret, references it in a `ComputeInstance` spec, provisions the instance, and verifies the instance reaches `Provisioned` state.
- Tenant User lists secrets: response contains metadata but no payload bytes for any entry.
- Tenant User retrieves kubeconfig for a provisioned `ClusterOrder` via `GetSecret(include_payload=true)` and authenticates against the cluster.
- Tenant Admin creates a secret, grants Tenant User access, Tenant User retrieves it; a second Tenant User (no grant) gets `PERMISSION_DENIED`.
- Cross-tenant isolation: Tenant A's secret ID submitted by Tenant B's authenticated client returns `NOT_FOUND` (not `PERMISSION_DENIED`, to avoid information disclosure).
- `DeleteSecret` on a referenced secret returns `FAILED_PRECONDITION`; after the referencing resource is deleted, `DeleteSecret` succeeds.

Reference: osac-test-infra pytest patterns. [Codebase: osac-test-infra]

## Graduation Criteria

### Dev Preview (OSAC 0.2)

- `SecretService` CRUD API is functional with HashiCorp Vault / OpenBao KV v2 backend.
- Tenant-scoped isolation verified by integration tests.
- System-created secrets (kubeconfig) written by `osac-operator` for `ClusterOrder`.
- Unit and integration test coverage ≥ 80% for new `fulfillment-service` secret package.
- Installer documentation covers Vault prerequisite deployment.

### Tech Preview

- At least one additional `SecretBackend` adapter validated (e.g., AWS Secrets Manager or Azure Key Vault) [Assumption — driven by cloud provider demand].
- E2E tests passing in CI against a real Vault HA deployment.
- API reference documentation published.
- All four personas' workflows documented in user guide.

### GA

- No breaking API changes since Tech Preview.
- All E2E tests passing reliably (< 1% flake rate).
- Vault path orphan cleanup mechanism implemented and tested (resolution of Open Question 1).
- Vault auth method finalized and documented (resolution of Open Question 2).
- Operator service-account token model finalized (resolution of Open Question 3).
- Security review completed.

## Upgrade / Downgrade Strategy

**Upgrade (adding `Secret` resource):** The `secrets` PostgreSQL table is additive. Existing OSAC resources are unaffected. Existing credential fields on other resources (e.g., raw kubeconfig in `ClusterOrder`) remain functional; migration to `Secret` references is deferred. Operators must configure the Vault backend connection in the installer before the `fulfillment-service` version with Secret support is deployed. [PRD: In Scope — Installation]

**Downgrade:** Remove the `secrets` table and `SecretService` registration. Any resource specs referencing a `Secret` by ID will hold a dangling ID; the referencing resources themselves are not deleted. [Assumption — downgrade requires manual cleanup of resource spec references]

No controller-level CRDs are introduced; downgrade does not require CRD removal.

## Version Skew Strategy

`SecretService` is introduced as a new gRPC service; existing clients that do not call it are unaffected during a rolling upgrade. An `osac-operator` version that calls `CreateSecret` running against an older `fulfillment-service` that lacks `SecretService` will receive `UNIMPLEMENTED`; the operator should log a warning and skip secret creation until the API server is upgraded. [Assumption]

During a rolling upgrade, the older `fulfillment-service` pods continue to serve all existing RPCs. The new `SecretService` RPC is only served by upgraded pods. Because operator retries are idempotent (display_name uniqueness), partial exposure of the new pods does not cause inconsistency.

## Support Procedures

**Detecting failures:**

- `UNAVAILABLE` errors on `SecretService` RPCs indicate Vault connectivity issues. Check `fulfillment-service` pod logs for `"vault write failed"` / `"vault read failed"` structured log entries.
- `SecretReady=False` condition on a `Secret` resource indicates a backend operation that did not complete; `reason` field names the failure category (e.g., `VaultUnavailable`).
- Vault audit logs provide a trail of all read/write operations indexed by Vault path, correlatable to OSAC secret IDs.

**Disabling the API extension:**

If `SecretService` must be disabled, remove the service registration from `fulfillment-service`. This causes all `SecretService` RPC calls to return `UNIMPLEMENTED`. Existing `Secret` metadata rows and Vault paths are preserved; no data is lost. Provisioning workflows that depend on automatic secret creation will log errors and may leave resources in a degraded state until the service is re-enabled.

**Resumability:** When `SecretService` is re-enabled, the operator's controller will re-reconcile pending system-created secrets; idempotency ensures no duplicates are created (display_name uniqueness per tenant).

## Infrastructure Needed

- A Vault-compatible secret store (HashiCorp Vault ≥ 1.12 or OpenBao ≥ 1.0) deployed and accessible from `fulfillment-service`. The cloud provider is responsible for this deployment. [PRD: Dependencies]
- Installer (`osac-installer`) must be extended with Vault connection configuration (address, mount path, TLS CA, initial token or AppRole credentials) as a new prerequisite section.
- CI/CD: a Vault dev server container added to the integration-test `kind` cluster setup in `osac-test-infra` to support integration tests without requiring a live Vault deployment.