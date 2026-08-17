---

```yaml
---
title: secret-management
authors:
  - Dakota Crowder
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
2. **`osac-operator`** — adds a `Secret` controller that writes system-generated secrets (e.g., kubeconfigs, admin passwords retrieved from the management cluster) into the backend via the fulfillment-service API after resource provisioning completes.
3. **`osac-aap`** — no new playbooks are required for this EP. All system-generated secret types (kubeconfigs, admin passwords) are retrieved by the operator from the management cluster post-provisioning and written via the fulfillment-service API. No AAP playbook generates credentials and writes them directly to Vault. If a future provisioning workflow requires a playbook to write a credential, a follow-on EP will address AAP integration. [Assumption — all system credentials are retrievable from the management cluster by the operator]

The PostgreSQL `secrets` table stores only the `Secret` resource metadata (id, tenant, name, type, backend reference path, conditions). The actual payload bytes are stored under a per-tenant path hierarchy in Vault (`osac/<tenant-id>/secrets/<secret-id>`), encrypted by Vault's transit engine. [PRD: In Scope]

A `SecretBackend` interface in Go is introduced in `fulfillment-service`, with a Vault adapter as the first implementation. Future adapters (AWS Secrets Manager, Azure Key Vault) can be registered without API changes. [PRD: In Scope — pluggable backends]

### Workflow Description

#### Workflow 1 — Tenant User creates a self-service secret

**Starting state:** Tenant User is authenticated; tenant already exists.

1. Tenant User calls `CreateSecret` with `spec.type = SSH_KEY`, `spec.display_name`, and `spec.payload` (base64-encoded private key).
2. `fulfillment-service` validates the request (type is a known enum value; payload is non-empty; name is unique within the tenant; `owner_reference` is absent or valid UUID of an existing resource).
3. fulfillment-service writes the encrypted payload to Vault at path `osac/<tenant-id>/secrets/<new-secret-id>` using the tenant-scoped Vault token resolved for this tenant. [PRD: In Scope — tenant-scoped privilege isolation]
4. fulfillment-service attempts to create a `secrets` database row with the backend path and initial condition `SecretReady=True`.
   - **If the DB INSERT fails:** fulfillment-service immediately calls `Delete(path)` on the Vault backend to compensate. If the compensating delete also fails, the path is recorded in an internal `vault_orphans` table (see [Vault/DB Atomicity](#vaultdb-atomicity)) for reconciler cleanup. The RPC returns `INTERNAL`.
5. Response returns the `Secret` resource with **`status.conditions`** set; `spec.payload` is **omitted** from the response.
6. Tenant User can now reference the `Secret` by `id` in other resource specs (e.g., `ComputeInstanceSpec.ssh_key_secret_id`).

Because `CreateSecret` is synchronous and the Vault write must succeed before the DB row is created, `SecretReady` is never set to `Unknown`; it is `True` on successful creation or the RPC returns an error and no row is written.

#### Workflow 2 — Tenant User retrieves a secret payload

**Starting state:** Secret exists; Tenant User has `secrets:read-payload` permission.

1. Tenant User calls `GetSecret` with `{id}` and query parameter `include_payload=true`.
2. fulfillment-service reads the Vault path from the `secrets` row, fetches the payload from Vault, and returns `spec.payload` populated in the response.
3. If `include_payload=false` (default), the payload field is suppressed; only metadata is returned. [PRD: User Story — list secrets without exposing data]
4. If the secret's `tenant_id` does not match the caller's authenticated tenant, the server returns `NOT_FOUND` — not `PERMISSION_DENIED` — to avoid disclosing that the secret exists in another tenant.

```
Tenant User ──CreateSecret(payload)──► fulfillment-service ──write──► Vault
                                            │                              │
                                         (success)              (fail → compensating Delete)
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
2. Controller calls `CreateSecret` on the fulfillment-service API using the operator service account. The request includes `spec.type = KUBECONFIG`, `spec.owner_reference = <ClusterOrder id>`, a deterministic `spec.display_name` of the form `system:<resource-type>:<resource-id>:<secret-type>` (e.g., `system:clusterorder:abc123:kubeconfig`), and the retrieved kubeconfig bytes as payload.
3. fulfillment-service stores the payload in Vault (using the operator's write-capable token) and writes the metadata row.
4. Controller patches the owning resource's status with `status.kubeconfig_secret_id = <new-secret-id>`.
5. Tenant User retrieves the kubeconfig via `GetSecret(id, include_payload=true)` — identical to any other secret. [PRD: User Story — credential access consistent regardless of how the secret was created]
6. **Idempotency on controller restart:** If the controller restarts and calls `CreateSecret` again with the same deterministic `display_name`, the server returns `ALREADY_EXISTS`. The controller detects this, calls `ListSecrets` filtered by `display_name` prefix to find the existing secret ID, and patches the owning resource status accordingly. No duplicate secret is created.

#### Workflow 4 — Tenant User deletes a secret

1. Tenant User calls `DeleteSecret(id)`.
2. fulfillment-service checks whether any resource references this secret via `owner_reference` or foreign-key lookup. If in use, returns `FAILED_PRECONDITION`. [PRD: User Story — delete a secret]
3. fulfillment-service marks the `secrets` DB row with `deleting = true` (soft-delete marker) so concurrent reads degrade gracefully.
4. fulfillment-service calls Vault to delete (destroy) the secret version at `osac/<tenant-id>/secrets/<secret-id>`.
   - If the Vault delete fails, the `deleting` marker is cleared and the server returns `UNAVAILABLE`. The secret remains fully accessible. Caller may retry.
   - If the Vault delete succeeds but the subsequent DB DELETE fails, a `vault_orphans` record is not needed (Vault is already clean); the DB row is left with `deleting = true` and the periodic reconciler removes it.
5. fulfillment-service hard-deletes the database row.
6. Response: empty (204 equivalent at REST layer).

#### Error Flows

| Situation | gRPC Code | Detail |
|-----------|-----------|--------|
| Payload empty on create | `INVALID_ARGUMENT` | `"spec.payload must not be empty"` |
| Unknown `spec.type` | `INVALID_ARGUMENT` | `"spec.type is not a recognized SecretType"` |
| Name collision within tenant | `ALREADY_EXISTS` | `"a secret with this name already exists in the tenant"` |
| Secret not found | `NOT_FOUND` | `"secret {id} not found"` |
| Secret belongs to a different tenant | `NOT_FOUND` | `"secret {id} not found"` (tenant boundary not disclosed) |
| Caller lacks read-payload permission | `PERMISSION_DENIED` | `"caller does not have secrets:read-payload"` |
| Secret in use on delete | `FAILED_PRECONDITION` | `"secret {id} is referenced by {resource-type} {resource-id}"` |
| Vault unreachable on write | `UNAVAILABLE` | retried by controller; exposed as condition `SecretReady=False, reason=VaultUnavailable` |
| Concurrent update conflict | `ABORTED` | `"resource version conflict; retry the operation"` |
| Immutable field (`type`) sent in update | `INVALID_ARGUMENT` | `"field type is immutable"` |
| `owner_reference` does not resolve to an existing resource | `INVALID_ARGUMENT` | `"owner_reference {id} does not reference a known resource"` |
| Vault delete succeeds, DB DELETE fails | — | Row left with `deleting=true`; reconciler cleans up; secret appears deleted to callers |

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
import "google/protobuf/field_mask.proto";
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
  // Immutable after creation — cannot be changed via UpdateSecret.
  SecretType type = 2;

  // payload holds the raw secret bytes (base64-encoded in JSON transcoding).
  // On responses, this field is omitted unless include_payload=true is requested.
  // payload is NEVER included in ListSecrets responses regardless of request flags.
  // [PRD: User Story — list secrets without exposing data]
  bytes payload = 3;

  // owner_reference optionally links system-created secrets to their originating resource.
  // Must be a valid UUID of an existing OSAC resource if provided.
  // Set by the operator for system-generated secrets; omitted for self-service secrets.
  // Self-service callers may not set owner_reference; the field is ignored if provided
  // by a non-operator caller.
  // Deleting the owner resource does NOT cascade-delete its secrets; explicit deletion is required.
  string owner_reference = 4;
}

// UpdateSecretSpec contains only the fields that may be changed after creation.
// Sending spec.type or spec.owner_reference in an UpdateSecretRequest returns INVALID_ARGUMENT.
message UpdateSecretSpec {
  // display_name may be changed. Must remain unique within the tenant.
  string display_name = 1;

  // payload replaces the stored secret bytes. Must be non-empty.
  bytes payload = 2;
}

message SecretStatus {
  repeated Condition conditions = 1;
  // vault_path is intentionally omitted from the API response.
  // It is stored in the DB and visible to operators via the DB or admin tooling only.
  // Exposing the Vault path structure to API callers is an unnecessary information disclosure.
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
  // page_size defaults to 50 if 0 or unset; maximum is 500.
  int32  page_size  = 3;
  // Optional filter by type.
  SecretType type_filter = 4;
}

// ListSecretsResponse never includes spec.payload for any entry.
// Use GetSecret with include_payload=true to retrieve a payload.
message ListSecretsResponse {
  repeated Secret secrets         = 1;
  string          next_page_token = 2;
}

message UpdateSecretRequest {
  string          tenant_id = 1;
  string          id        = 2;
  // spec contains only the mutable fields display_name and payload.
  // Attempting to set type or owner_reference returns INVALID_ARGUMENT.
  UpdateSecretSpec spec     = 3;
  // resource_version must match the current value to prevent lost updates.
  int64           resource_version = 4;
}

message DeleteSecretRequest {
  string tenant_id = 1;
  string id        = 2;
}
```

### Database Schema

```sql
CREATE TABLE secrets (
  id               UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id        UUID        NOT NULL REFERENCES tenants(id),
  display_name     TEXT        NOT NULL,
  type             TEXT        NOT NULL,
  vault_path       TEXT        NOT NULL,
  owner_reference  UUID,                          -- nullable; set for system-created secrets
  resource_version BIGINT      NOT NULL DEFAULT 0,
  deleting         BOOLEAN     NOT NULL DEFAULT false,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  conditions       JSONB       NOT NULL DEFAULT '[]'
);

CREATE UNIQUE INDEX secrets_tenant_name_uidx
  ON secrets(tenant_id, display_name);

-- vault_orphans tracks Vault paths written when the subsequent DB INSERT failed
-- and the compensating Vault delete also failed. The periodic reconciler
-- reads this table and retries the Vault delete.
CREATE TABLE vault_orphans (
  id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  vault_path  TEXT        NOT NULL,
  tenant_id   UUID        NOT NULL,
  detected_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Immutable fields: id, tenant_id, type, vault_path (enforce via trigger Z0001)
-- Delete protection: check references before delete (Z0003 logic in application layer)
-- soft-delete: deleting=true rows are excluded from List results and return NOT_FOUND on Get
```

`spec.type` and `vault_path` are immutable after creation (enforced by a PostgreSQL trigger raising SQLSTATE `Z0001`). Attempts to change them are translated to `INVALID_ARGUMENT` by `translateError`. [Codebase: fulfillment-service/internal/db/errors.go]

### Vault/DB Atomicity

Vault and PostgreSQL have no distributed transaction. The following protocol minimises the window for inconsistency on Create:

1. Generate `secret_id` (UUID) in the application layer before any I/O.
2. Derive the Vault path: `osac/<tenant-id>/secrets/<secret-id>`.
3. Call `Vault.Write(path, payload)`.
4. Attempt `DB.INSERT` into `secrets`.
5. **If INSERT succeeds:** return success.
6. **If INSERT fails:**
   a. Call `Vault.Delete(path)` to compensate.
   b. If compensating delete succeeds: return `INTERNAL` (no orphan).
   c. If compensating delete also fails: insert a row into `vault_orphans(vault_path, tenant_id)` — this insert uses a separate DB connection/transaction so it is not affected by the original failure. Return `INTERNAL`.

**Orphan reconciler** (runs in `fulfillment-service`, period configurable, default 5 minutes):
- SELECT all rows from `vault_orphans`.
- For each row, attempt `Vault.Delete(path)`.
- On success, delete the `vault_orphans` row.
- On failure, leave the row for the next cycle and emit a warning log with the path and age.
- The reconciler lives in the `fulfillment-service` secret package alongside the service handler.

This design is chosen over Vault leases because leases require Vault Enterprise or specific mount configuration, whereas the orphan table approach works with any KV v2 mount. [Open Question 1 resolved]

### Vault Backend Interface

```go
// SecretBackend is the abstraction layer for pluggable secret stores.
// Each method receives a tenantID so the adapter can resolve the appropriate
// tenant-scoped credential (token, role, etc.) for the operation.
// [PRD: In Scope — pluggable secret backends; tenant-scoped privilege isolation]
type SecretBackend interface {
    // Write stores or overwrites the payload at the given path, operating under
    // the credential scoped to tenantID.
    Write(ctx context.Context, tenantID, path string, payload []byte) error
    // Read retrieves the payload. Returns (nil, ErrNotFound) if absent.
    // Operates under the credential scoped to tenantID.
    Read(ctx context.Context, tenantID, path string) ([]byte, error)
    // Delete permanently destroys the secret at path.
    // Operates under the credential scoped to tenantID.
    Delete(ctx context.Context, tenantID, path string) error
    // WriteAsOperator stores a payload under the operator's write-capable credential,
    // bypassing the per-tenant token. Used exclusively by the operator service account
    // when creating system-generated secrets.
    WriteAsOperator(ctx context.Context, path string, payload []byte) error
}
```

The initial implementation (`VaultBackend`) uses HashiCorp/OpenBao KV v2 with the Vault Go SDK. The backend is configured via `fulfillment-service` operator config (mount path, address, TLS CA, AppRole credentials for both per-tenant and operator access). [Open Question 2 resolved — AppRole auth; see Vault Auth Model below]

### Vault Auth Model

**Initial implementation: AppRole auth.**

Two AppRole roles are configured at installation time:

| Role | Vault Policy | Used By |
|---|---|---|
| `osac-tenant-<tenant-id>` | `path "osac/<tenant-id>/*" { capabilities = ["create","read","delete"] }` | `VaultBackend` per-tenant operations (Write/Read/Delete) |
| `osac-operator` | `path "osac/*/secrets/*" { capabilities = ["create","delete"] }` (write and delete only, no read) | Operator service account creating/deleting system-generated secrets |

The `VaultBackend` maintains a `TokenCache` keyed by `tenantID`. On first access for a tenant, the adapter performs an AppRole login using the role ID and secret ID for that tenant (obtained from installer-provisioned configuration) and caches the resulting token. Tokens are refreshed before expiry using Vault's token renewal API.

On Vault 403 (token expired or revoked), the adapter clears the cache entry, re-authenticates once, and retries the operation. If the retry also fails, the operation returns an error that the service layer translates to `UNAVAILABLE`.

The `osac-operator` role intentionally has no `read` capability. This means:
- The operator can write system-generated secrets on behalf of a tenant (e.g., kubeconfigs).
- The operator cannot read back secret payloads, maintaining read isolation.
- Tenant users retrieve payloads via the per-tenant token path, which the fulfillment-service uses on their behalf.

AppRole role IDs and secret IDs for each tenant are provisioned by the installer when a tenant is created and stored in a fulfillment-service configuration secret (not in the OSAC database). [PRD: Dependencies — cloud provider deploys and operates the secret store]

[Open Questions 2 and 3 resolved]

### Vault Path Convention

```
osac/<tenant-id>/secrets/<secret-id>
```

Each tenant's secrets are grouped under their own Vault path prefix. The per-tenant AppRole token is scoped exclusively to `osac/<tenant-id>/*`, satisfying tenant-scoped privilege isolation. The operator AppRole token has write-only access to `osac/*/secrets/*`. [PRD: In Scope — OSAC limits its access to only a tenant's secrets]

The `vault_path` value is stored in the `secrets` DB table for operational cross-referencing. It is **not** returned in any API response. Operators requiring the path for Vault audit log correlation must query the DB directly or use an admin API endpoint outside this EP's scope.

### Payload Handling

- `spec.payload` is never written to PostgreSQL.
- `spec.payload` is omitted from all responses unless `GetSecretRequest.include_payload = true`.
- `ListSecrets` **never** returns payloads, regardless of request flags. [PRD: User Story — list secrets without exposing data]
- Payload bytes are validated to be non-empty on Create and Update.

### List Pagination Semantics

`ListSecrets` uses opaque cursor-based pagination:

- **Default page size:** 50. **Maximum page size:** 500. A `page_size` of 0 or negative is treated as the default.
- **Sort order:** `created_at DESC`, then `id ASC` as a tiebreaker for stable ordering.
- **Cursor:** `page_token` is an opaque base64-encoded string encoding `(created_at, id)` of the last item on the previous page. Clients must not parse or construct tokens.
- **Empty `page_token`:** returns the first page.
- **`next_page_token` absent or empty:** indicates no further pages.
- `payload` is always omitted from list responses. Secrets with `deleting = true` are excluded.

### System-Created Secret Naming Convention

System-generated secrets use a deterministic `display_name` following the pattern:

```
system:<resource-type>:<resource-id>:<secret-type>
```

Examples:
- `system:clusterorder:abc123:kubeconfig`
- `system:baremetalhost:def456:admin-password`

This naming convention is enforced by the operator before calling `CreateSecret`. It guarantees idempotent retry behaviour: if the operator calls `CreateSecret` with the same display_name and receives `ALREADY_EXISTS`, it resolves the existing secret ID via `ListSecrets` and proceeds without creating a duplicate. Self-service callers may not use the `system:` prefix; the server rejects `display_name` values starting with `system:` from non-operator callers with `INVALID_ARGUMENT`.

### `owner_reference` Semantics

- `owner_reference` is optional. If provided, it must be a valid UUID of an existing OSAC resource; fulfillment-service validates the reference at creation time. An invalid UUID or a UUID that does not resolve to a known resource returns `INVALID_ARGUMENT`.
- Self-service (non-operator) callers may not set `owner_reference`. The field is rejected with `INVALID_ARGUMENT` if provided by a caller without the operator service account role.
- Deleting the owner resource does **not** cascade-delete its associated secrets. The `owner_reference` is informational. Tenant Admins must explicitly delete orphaned secrets after the owner resource is removed.
- The proto field is `string` (UUID string form); the DB column is `UUID`. The service layer converts between the two on read and write.

### CRUD Operation Details

| Operation | Validation | Vault Op | DB Op | Error Codes |
|-----------|-----------|----------|-------|-------------|
| **Create** | type known; payload non-empty; display_name unique; owner_reference valid if present; non-operator callers cannot set owner_reference or display_name with `system:` prefix | `Write(tenantID, path, payload)` | `INSERT` | `INVALID_ARGUMENT`, `ALREADY_EXISTS` |
| **Get** | secret's tenant_id matches caller's tenant (else NOT_FOUND) | `Read(tenantID, path)` if include_payload | `SELECT` (excludes deleting=true rows) | `NOT_FOUND`, `PERMISSION_DENIED` |
| **List** | tenant scoped; excludes deleting=true rows | none | `SELECT WHERE tenant_id=? AND deleting=false` | — |
| **Update** | payload non-empty; display_name unique if changed; type/vault_path/owner_reference immutable; resource_version must match | `Write(tenantID, path, payload)` | `UPDATE` + Z0001 check | `INVALID_ARGUMENT`, `NOT_FOUND`, `ABORTED` |
| **Delete** | no resource references this secret; sets deleting=true before Vault op | `Delete(tenantID, path)` | soft then hard `DELETE` | `NOT_FOUND`, `FAILED_PRECONDITION`, `UNAVAILABLE` |

### Security Considerations

**Encryption at rest.** Vault's KV v2 encryption-as-a-service ensures payloads are encrypted. The OSAC PostgreSQL database never holds the plaintext. [PRD: User Story — Cloud Infrastructure Admin]

**Tenant isolation.** Each tenant has a dedicated AppRole in Vault scoped to `osac/<tenant-id>/*`. The fulfillment-service resolves the per-tenant AppRole token for each operation. OPA policies additionally filter list results to the caller's tenant, enforced at the gRPC interceptor layer consistent with existing resources. [PRD: In Scope — tenant-scoped privilege isolation]

**Cross-tenant access.** A caller requesting a secret whose `tenant_id` does not match their authenticated tenant receives `NOT_FOUND`, not `PERMISSION_DENIED`, to avoid information disclosure about the existence of secrets in other tenants.

**Vault path not exposed to callers.** `vault_path` is stored in the DB for operational use only and is not returned in any API response. This prevents the Vault address structure from leaking to API consumers.

**Operator isolation.** The operator service account uses a separate AppRole (`osac-operator`) with write-only access (`create` and `delete` capabilities, no `read`). The operator can deposit system-generated secrets but cannot retrieve tenant payloads.

**Payload exposure.** `GetSecret` with `include_payload=true` is an audited operation. Access is gated on the `secrets:read-payload` permission, which is granted only to the secret owner and Tenant Admins by default. [PRD: User Story — Tenant Admin controls RBAC]

**Payload logging.** gRPC interceptors must scrub `spec.payload` from structured logs. A `SecretSpec` log sanitizer is implemented in the `fulfillment-service` logging middleware. [Assumption — sanitizer implementation detail]

**Immutable fields.** `spec.type` and `vault_path` cannot be changed after creation; enforced at DB layer (Z0001) and at the proto layer (the `UpdateSecretRequest` uses `UpdateSecretSpec` which does not contain these fields). This double enforcement ensures callers receive a clear error at the application layer before any DB operation.

**Input validation.** `display_name` is validated for length (≤ 255 chars) and printable UTF-8. `payload` must be non-empty bytes. [Assumption — max display_name length]

### Failure Handling and Recovery

| Failure Mode | What Happens | Recovery | User Observes |
|---|---|---|---|
| Vault unreachable on `CreateSecret` | Write to Vault fails; DB row is not created | Server returns `UNAVAILABLE`; client retries | `UNAVAILABLE` gRPC error |
| Vault write succeeds, DB INSERT fails, compensating delete succeeds | No DB row, no Vault path | Server returns `INTERNAL`; client retries with new UUID | `INTERNAL`; clean state |
| Vault write succeeds, DB INSERT fails, compensating delete fails | Vault path orphaned; recorded in `vault_orphans` | Periodic reconciler retries Vault delete; emits warning log until resolved | `INTERNAL`; client retries |
| Vault unreachable on `GetSecret(include_payload=true)` | Metadata retrieved from DB; Vault read fails | Server returns `UNAVAILABLE` | `UNAVAILABLE`; metadata visible via `include_payload=false` |
| Vault delete fails on `DeleteSecret` | `deleting=true` marker cleared; DB row remains intact | Returns `UNAVAILABLE`; secret fully accessible; caller retries | `UNAVAILABLE`; secret still visible |
| Vault delete succeeds, DB DELETE fails | Row left with `deleting=true`; payload gone from Vault | Reconciler removes the DB row; secret appears deleted to callers (excluded from List/Get) | No user-visible disruption after reconciler runs |
| Immutable field update attempted | `UpdateSecretSpec` does not contain the field; server rejects any unknown field | `INVALID_ARGUMENT: field type is immutable` returned before DB op | `INVALID_ARGUMENT` |
| Secret in use on delete | Application-layer check finds referencing resource | Returns `FAILED_PRECONDITION` | `FAILED_PRECONDITION: secret {id} is referenced by {type} {id}` |
| Concurrent `UpdateSecret` conflict | `resource_version` mismatch detected | Returns `ABORTED` | `ABORTED: resource version conflict; retry` |
| Controller restart mid-creation | Operator re-reconciles; calls `CreateSecret` again with deterministic display_name | `ALREADY_EXISTS` from server; controller resolves existing secret ID via ListSecrets | No user-visible disruption |
| Vault token expired during operation | Vault SDK returns 403; adapter clears cache, re-authenticates, retries once | Returns `UNAVAILABLE` on second failure | `UNAVAILABLE` |
| `owner_reference` UUID not found | Validation fails before any Vault or DB op | Returns `INVALID_ARGUMENT` | `INVALID_ARGUMENT: owner_reference {id} does not reference a known resource` |

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
| System (operator service account) | ✓ (system secret types only; sets `system:` display_name prefix and owner_reference) | ✗ | ✗ | ✗ | ✗ | ✓ (system-owned secrets only) |

[PRD: User Story — Tenant Admin controls RBAC]

The operator service account is configured at installation time and is not a human persona. It authenticates using the `osac-operator` AppRole credential and is granted Create/Delete only for system-generated secret types (`KUBECONFIG`, etc.). It cannot read payloads.

System-created secrets (kubeconfigs, admin passwords) are owned by the provisioning controller and visible (metadata + payload with `read-payload` permission) to the tenant that owns the parent resource.

### Observability and Monitoring

No new observability changes beyond what is described here. Existing monitoring mechanisms apply.

Vault's native audit log is the primary audit trail for payload access, indexed by Vault path (correlatable to OSAC secret IDs via the DB `vault_path` column, accessible to operators). The `vault_path` is not exposed in API responses; operators requiring path correlation must query the DB.

The `vault_orphans` table serves as an operational signal: a growing table indicates persistent Vault connectivity or auth issues. An alert on `vault_orphans` row count exceeding a threshold (e.g., 10 rows) should be added to the fulfillment-service runbook.

### Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Vault becomes a single point of failure for all credential access | Cloud providers must deploy Vault in HA configuration; OSAC returns `UNAVAILABLE` gracefully rather than corrupting state |
| Tenant isolation misconfiguration in Vault AppRole policies | Integration tests explicitly verify cross-tenant access is denied; OPA policies add a second enforcement layer |
| Payload accidentally logged | gRPC interceptors scrub `spec.payload` from structured logs via a `SecretSpec` log sanitizer |
| Vault path orphans if DB transaction fails and compensating delete fails | `vault_orphans` table + periodic reconciler cleans up; alert on table growth |
| Operator holding write-capable token broader than per-tenant scope | Operator AppRole has no `read` capability; write-only access to `osac/*/secrets/*`; cannot exfiltrate payloads |
| Vault token cache race condition under high concurrency | Token cache uses a per-tenant mutex; stale entries trigger a single re-auth, not a stampede |

### Drawbacks

- **Operational dependency.** OSAC now requires an external Vault-compatible store to be healthy for any secret CRUD operation. This increases deployment complexity and operator burden.
- **Partial atomicity.** Vault and PostgreSQL are two separate data stores with no distributed transaction. The compensating-delete + orphan-reconciler approach handles the failure modes but adds implementation complexity.
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

### Alternative 4 — Vault leases as orphan cleanup mechanism

Use short-lived Vault leases on KV entries so that an orphaned path expires automatically if the DB INSERT fails.

**Rejected because:** KV v2 does not support leases on static secrets in the same way as dynamic secrets. This would require Vault Enterprise features or a non-standard KV mount configuration. The orphan table + reconciler approach is portable across all Vault-compatible stores.

## Open Questions

~~1. **Vault path orphan cleanup**~~ — Resolved: compensating-delete on DB INSERT failure + `vault_orphans` table + periodic reconciler. See [Vault/DB Atomicity](#vaultdb-atomicity).

~~2. **Vault auth method**~~ — Resolved: AppRole auth. See [Vault Auth Model](#vault-auth-model).

~~3. **Operator service-account token**~~ — Resolved: separate `osac-operator` AppRole with write-only access to `osac/*/secrets/*`. See [Vault Auth Model](#vault-auth-model).

4. **`spec.type` immutability UX** — Is it acceptable that a caller cannot change the type of a secret (e.g., cannot re-classify a `GENERIC` secret as `SSH_KEY`)? Or should type be mutable with appropriate re-validation? Current design: immutable. Revisit if user feedback indicates a need.

## Test Plan

### Unit Tests

- `SecretSpec` validation rejects empty payload with `INVALID_ARGUMENT`.
- `SecretSpec` validation rejects unknown `type` enum values with `INVALID_ARGUMENT`.
- `UpdateSecretRequest` with `type` set in the spec returns `INVALID_ARGUMENT: field type is immutable` (application-layer enforcement via `UpdateSecretSpec`).
- `translateError` maps DB SQLSTATE `Z0001` to `INVALID_ARGUMENT` for immutable field violations on `type` and `vault_path`.
- `translateError` maps DB SQLSTATE `Z0003` to `FAILED_PRECONDITION` for delete-protection violations.
- `ListSecretsResponse` never includes `spec.payload` regardless of request flags.
- `GetSecret` with `include_payload=false` returns `spec.payload` as nil/empty.
- `GetSecret` with a secret ID belonging to a different tenant returns `NOT_FOUND` (not `PERMISSION_DENIED`).
- `VaultBackend.Write` followed by `VaultBackend.Read` returns original bytes (round-trip test with Vault dev server).
- `VaultBackend.Delete` followed by `VaultBackend.Read` returns `ErrNotFound`.
- Concurrent `UpdateSecret` with mismatched `resource_version` returns `ABORTED`.
- Vault path convention generates `osac/<tenant-id>/secrets/<secret-id>` correctly.
- Compensating delete is called when DB INSERT fails after Vault write succeeds.
- `vault_orphans` row is inserted when both DB INSERT and compensating Vault delete fail.
- Orphan reconciler: row is removed from `vault_orphans` after successful Vault delete.
- `display_name` starting with `system:` from a non-operator caller returns `INVALID_ARGUMENT`.
- `owner_reference` set by non-operator caller returns `INVALID_ARGUMENT`.
- `owner_reference` referencing an unknown UUID returns `INVALID_ARGUMENT`.
- `ListSecrets` with `page_size=0` applies the default of 50.
- `ListSecrets` with `page_size > 500` is clamped to 500.
- Results are ordered `created_at DESC, id ASC`.
- Secrets with `deleting=true` are excluded from List and return `NOT_FOUND` on Get.

### Integration Tests

- `CreateSecret` with valid `SSH_KEY` payload writes to Vault KV v2 and returns a `Secret` with `SecretReady=True` condition; DB row contains correct `vault_path`; `vault_path` is not present in the API response.
- `GetSecret` without `include_payload=true` does not call Vault (verified by mock/spy).
- `GetSecret` with `include_payload=true` retrieves and returns the correct payload bytes.
- `GetSecret` with a valid UUID belonging to a different tenant returns `NOT_FOUND`.
- `ListSecrets` returns metadata for all secrets scoped to the caller's tenant; omits secrets of other tenants; never includes payload bytes.
- `ListSecrets` pagination: second page token returns the correct next page; final page has empty `next_page_token`.
- `UpdateSecret` replaces the Vault payload; `resource_version` increments in the DB row.
- `UpdateSecret` with `type` field present returns `INVALID_ARGUMENT` (proto shape enforces this at the message level).
- `DeleteSecret` for a secret referenced by a `ComputeInstance.ssh_key_secret_id` returns `FAILED_PRECONDITION`.
- `DeleteSecret` for an unreferenced secret removes both the Vault path and the DB row; subsequent `GetSecret` returns `NOT_FOUND`.
- Immutable field update (`spec.type` change) returns `INVALID_ARGUMENT`.
- System-created secret: operator service account calls `CreateSecret` with `system:` display_name prefix and `owner_reference`; secret is stored; parent resource status is patched with `kubeconfig_secret_id`.
- Non-operator caller setting `owner_reference` returns `INVALID_ARGUMENT`.
- Non-operator caller using `system:` display_name prefix returns `INVALID_ARGUMENT`.
- Vault unavailable (simulated): `CreateSecret` returns `UNAVAILABLE`; no DB row is inserted.
- DB INSERT failure after Vault write (simulated): compensating delete is called; no DB row remains; `vault_orphans` row is created if compensating delete also fails.
- Orphan reconciler (simulated): pre-existing `vault_orphans` row causes reconciler to retry Vault delete; row is removed on success.
- Operator service account cannot read payloads (Vault policy enforced).

### E2E Tests

- Tenant User creates an `SSH_KEY` secret, references it in a `ComputeInstance` spec, provisions the instance, and verifies the instance reaches `Provisioned` state.
- Tenant User lists secrets: response contains metadata but no payload bytes for any entry.
- Tenant User retrieves kubeconfig for a provisioned `ClusterOrder` via `GetSecret(include_payload=true)` and authenticates against the cluster.
- Tenant Admin creates a secret, grants Tenant User access, Tenant User retrieves it; a second Tenant User (no grant) gets `PERMISSION_DENIED` on `include_payload=true` and `NOT_FOUND` if accessing a secret outside their tenant.
- Cross-tenant isolation: Tenant A's secret ID submitted by Tenant B's authenticated client returns `NOT_FOUND`.
- `DeleteSecret` on a referenced secret returns `FAILED_PRECONDITION`; after the referencing resource is deleted, `DeleteSecret` succeeds.
- Admin password secret created automatically during BMaaS provisioning; Tenant User retrieves it via `GetSecret`.

Reference: osac-test-infra pytest patterns. [Codebase: osac-test-infra]

## Graduation Criteria

### Dev Preview (OSAC 0.2)

- `SecretService` CRUD API is functional with HashiCorp Vault / OpenBao KV v2 backend.
- AppRole auth model implemented for both per-tenant and operator service account tokens.
- Tenant-scoped isolation verified by integration tests including cross-tenant `NOT_FOUND` check.
- System-created secrets (kubeconfig, admin password) written by `osac-operator` for `ClusterOrder` and BMaaS resources.
- Orphan reconciler implemented and tested.
- Unit and integration test coverage ≥ 80% for new `fulfillment-service` secret package.
- Installer documentation covers Vault prerequisite deployment, AppRole configuration per tenant, and operator AppRole setup.

### Tech Preview

- At least one additional `SecretBackend` adapter validated (e.g., AWS Secrets Manager or Azure Key Vault) [Assumption — driven by cloud provider demand].
- E2E tests passing in CI against a real Vault HA deployment.
- API reference documentation published.
- All four personas' workflows documented in user guide.

### GA

- No breaking API changes since Tech Preview.
- All E2E tests passing reliably (< 1% flake rate).
- Security review completed.
- Open Question 4 (`spec.type` immutability UX) resolved based on user feedback.

## Upgrade / Downgrade Strategy

**Upgrade (adding `Secret` resource):** The `secrets` and `vault_orphans` PostgreSQL tables are additive. Existing OSAC resources are unaffected. Existing credential fields on other resources (e.g., raw kubeconfig in `ClusterOrder`) remain functional; migration to `Secret` references is deferred. Operators must configure the Vault backend connection and AppRole credentials in the installer before the `fulfillment-service` version with Secret support is deployed. [PRD: In Scope — Installation]

**Downgrade:** Remove the `secrets`, `vault_orphans` tables and `SecretService` registration. Any resource specs referencing a `Secret` by ID will hold a dangling ID; the referencing resources themselves are not deleted. [Assumption — downgrade requires manual cleanup of resource spec references]

No controller-level CRDs are introduced; downgrade does not require CRD removal.

## Version Skew Strategy

`SecretService` is introduced as a new gRPC service; existing clients that do not call it are unaffected during a rolling upgrade. An `osac-operator` version that calls `CreateSecret` running against an older `fulfillment-service` that lacks `SecretService` will receive `UNIMPLEMENTED`; the operator should log a warning and skip secret creation until the API server is upgraded. [Assumption]

During a rolling upgrade, the older `fulfillment-service` pods continue to serve all existing RPCs. The new `SecretService` RPC is only served by upgraded pods. Because operator retries are idempotent (deterministic `display_name` uniqueness), partial exposure of the new pods does not cause inconsistency.

## Support Procedures

**Detecting failures:**

- `UNAVAILABLE` errors on `SecretService` RPCs indicate Vault connectivity issues. Check `fulfillment-service` pod logs for `"vault write failed"` / `"vault read failed"` structured log entries.
- `SecretReady=False` condition on a `Secret` resource indicates a backend operation that did not complete; `reason` field names the failure category (e.g., `VaultUnavailable`).
- A non-empty `vault_orphans` table indicates Vault operations that succeeded but whose compensating DB operation failed. Monitor row count; alert at threshold.
- Rows with `deleting=true` in the `secrets` table indicate secrets whose Vault payload has been deleted but whose DB row has not been cleaned up. The reconciler handles these; investigate if rows persist for more than one reconciler cycle.
- Vault audit logs provide a trail of all read/write operations indexed by Vault path, correlatable to OSAC secret IDs via the `vault_path` column in the `secrets` table (accessible to operators via DB).

**Disabling the API extension:**

If `SecretService` must be disabled, remove the service registration from `fulfillment-service`. This causes all `SecretService` RPC calls to return `UNIMPLEMENTED`. Existing `Secret` metadata rows and Vault paths are preserved; no data is lost. Provisioning workflows that depend on automatic secret creation will log errors and may leave resources in a degraded state until the service is re-enabled.

**Resumability:** When `SecretService` is re-enabled, the operator's controller will re-reconcile pending system-created secrets; idempotency via deterministic display_name ensures no duplicates are created.

## Infrastructure Needed

- A Vault-compatible secret store (HashiCorp Vault ≥ 1.12 or OpenBao ≥ 1.0) deployed and accessible from `fulfillment-service`. The cloud provider is responsible for this deployment. [PRD: Dependencies]
- Installer (`osac-installer`) must be extended with:
  - Vault connection configuration (address, KV v2 mount path, TLS CA).
  - AppRole provisioning for each tenant (`osac-tenant-<tenant-id>` role ID and secret ID).
  - AppRole provisioning for the operator service account (`osac-operator` role ID and secret ID).
  - Vault policy creation for both per-tenant and operator roles.
- CI/CD: a Vault dev server container added to the integration-test `kind` cluster setup in `osac-test-infra` to support integration tests without requiring a live Vault deployment.