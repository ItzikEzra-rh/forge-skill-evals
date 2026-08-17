## Design Document Review: Secret Management

---

### Overall Assessment

This is a high-quality design document. The structure is complete, the proto schema is well-formed, failure modes are concrete, and test scenarios are specific. The issues below are real deficiencies, not nitpicks, but none are blockers individually — the most critical ones cluster around the Vault/DB atomicity gap and a few self-contradictions.

---

## Issues

### CRITICAL

---

**1. Vault write / DB INSERT atomicity is unresolved but treated as if handled**
- **Category:** Depth / Consistency
- **Severity:** Critical
- **Problem:** The design correctly identifies the split-brain risk (Vault write succeeds, DB INSERT fails) in both the Failure Handling table and Risks section, but then defers the resolution to Open Question 1. However, the Create workflow (Workflow 1) describes the operation as if it is sequential and recoverable via simple retry — it is not. A retry generates a new UUID, leaving the first Vault path orphaned permanently. The failure table entry says "orphan cleanup via periodic reconciler [Assumption]" but no reconciler is designed anywhere.
- **Fix:** Either (a) specify the two-phase approach: write to Vault first, then INSERT with the Vault path; on INSERT failure, call `Delete(path)` to compensate, and document what happens if the compensating delete also fails; or (b) design the reconciler minimally — what it queries (Vault paths not present in DB), how often it runs, and where it lives. The graduation criteria correctly gates GA on this, but the design itself needs at least a sketch of the chosen approach so implementers are not blocked.

---

**2. `spec.type` immutability enforced at DB layer but `UpdateSecretRequest` proto accepts a full `Secret` with `type` field**
- **Category:** Consistency
- **Severity:** Critical
- **Problem:** `UpdateSecretRequest.secret` is typed as `Secret`, which contains `SecretSpec`, which contains `type`. The design says only `payload` and `display_name` are mutable, and the DB trigger enforces this. But the proto does not prevent a caller from sending `type` in an update — the server silently ignores it or the trigger fires. If the trigger fires, the caller gets `INVALID_ARGUMENT` without understanding why. If the field is silently ignored, the API is misleading.
- **Fix:** Either use a `FieldMask` in `UpdateSecretRequest` (idiomatic proto AIP-134 style, consistent with other OSAC update patterns if they use it), or replace the `Secret` field with a dedicated `UpdateSecretSpec` message that only contains `display_name` and `payload`. Document explicitly which fields are accepted in update; add a unit test that sending `type` in an update returns `INVALID_ARGUMENT` with message `"field type is immutable"` rather than relying on a DB trigger surprise.

---

**3. Vault token / auth model is unresolved but the security model depends on it entirely**
- **Category:** Depth
- **Severity:** Critical
- **Problem:** Tenant isolation at the Vault path level is the core security claim of this design. The mechanism that obtains per-tenant Vault tokens is entirely deferred to Open Questions 2 and 3, and contradictory statements exist: the Vault Path Convention section says "OSAC uses a Vault policy per tenant that scopes its token to only `osac/<tenant-id>/*`" but the Vault Backend Interface is a single shared `SecretBackend` instance with no tenant-scoped token parameter. The interface signature `Write(ctx, path, payload)` has no tenant credential parameter — there is no mechanism in the interface to pass or switch tenant-scoped tokens per call.
- **Fix:** The `SecretBackend` interface must be extended (e.g., `Write(ctx, tenantID, path, payload)`) or the adapter must accept a tenant-scoped credential resolver. The design must specify at least the initial auth model (AppRole recommended by Open Question 2 itself) even if alternatives are noted. The security section cannot assert tenant isolation while the mechanism for achieving it is entirely open.

---

### IMPORTANT

---

**4. `vault_path` exposed in `SecretStatus` is a security concern not addressed**
- **Category:** Depth / Completeness
- **Severity:** Important
- **Problem:** `SecretStatus.vault_path` is exposed to API callers for "auditability." But the vault path encodes the tenant ID and secret ID, and knowing it doesn't help a Tenant User audit anything — they cannot query Vault directly. More importantly, exposing the path to callers provides an information disclosure vector: a compromised client session reveals the Vault address structure. The security section does not address this.
- **Fix:** Either (a) remove `vault_path` from `SecretStatus` and keep it internal/DB-only (operators can look it up via DB or admin API), or (b) restrict it to Cloud Infrastructure Admin / Cloud Provider Admin roles only and add that to the RBAC table. Add a note in the Security Considerations section explaining the decision.

---

**5. `ListSecrets` has no server-side filtering beyond `type_filter` and `tenant_id`, but pagination semantics are unspecified**
- **Category:** Depth
- **Severity:** Important
- **Problem:** `ListSecretsRequest` has `page_token` and `page_size` but the design does not specify: what the token encodes (cursor vs. offset), what happens when `page_size` is 0 or negative, what the default page size is, or whether the list is ordered. This is a common omission but matters for implementation — especially since secrets with large counts (many SSH keys per tenant) will hit this.
- **Fix:** Add a subsection or inline note in CRUD Operation Details specifying: default page size (e.g., 50), maximum page size (e.g., 500), sort order (e.g., `created_at DESC`), and whether the cursor is opaque. This is consistent with how other OSAC list operations should be documented.

---

**6. Cross-tenant `NOT_FOUND` vs. `PERMISSION_DENIED` decision is stated in E2E tests but not in the API spec or error table**
- **Category:** Consistency / Depth
- **Severity:** Important
- **Problem:** The E2E test section correctly states: "Tenant B's secret ID submitted by Tenant B's client returns `NOT_FOUND` (not `PERMISSION_DENIED`, to avoid information disclosure)." This is a deliberate security decision. However, the error flows table does not list this case, and `GetSecret` workflow only mentions `PERMISSION_DENIED` for missing `read-payload` permission. An implementer reading only the API spec would implement `PERMISSION_DENIED` for cross-tenant access.
- **Fix:** Add a row to the error table: "Secret belongs to a different tenant | `NOT_FOUND` | `"secret {id} not found"` (tenant boundary not disclosed)." Update the `GetSecret` workflow description to state this explicitly.

---

**7. Operator authentication to Vault as tenant is architecturally conflated**
- **Category:** Depth / Consistency
- **Severity:** Important
- **Problem:** Workflow 3 (automatic secret creation) says the operator calls `CreateSecret` "on behalf of the resource owner." But `CreateSecret` in fulfillment-service writes to Vault using the tenant-scoped token. Open Question 3 asks whether the operator gets one token per tenant or a single broad token. If tenant-scoped tokens are used for isolation (the core security claim), the operator holding a broad token breaks the isolation model. If the operator uses a per-tenant token, the token provisioning for hundreds of tenants is a non-trivial operational problem.
- **Fix:** The design must pick a model and defend it. A reasonable answer: the operator uses a separate Vault policy (`osac/operator/*`) that allows write to any `osac/<tenant-id>/secrets/*` path but no read, and the operator token is a long-lived service account credential managed by the installer. Document this in Security Considerations and Infrastructure Needed. Do not leave this as entirely open — it affects the security boundary statement.

---

**8. `owner_reference` field type and semantics are underspecified**
- **Category:** Depth
- **Severity:** Important
- **Problem:** `SecretSpec.owner_reference` is `string` in the proto but `UUID` in the DB schema. More importantly, the design does not specify: what resource types can be an owner, whether the owner must exist at creation time (referential integrity), whether deleting the owner resource cascades to delete the secret, and how fulfillment-service validates the reference. Workflow 3 shows the operator setting it, but the validation rules are absent.
- **Fix:** Add a paragraph specifying: owner_reference is optional, must be a valid UUID of an existing OSAC resource if provided (validated by fulfillment-service), no cascade delete (secrets outlive their owner resource by default, requiring explicit deletion), and the DB column type should be consistent with the proto (`string` in proto, store as `UUID` in DB — document the conversion). The proto field comment says "Set by the operator; omitted for self-service secrets" but doesn't say callers cannot set it — is self-service creation with an owner_reference rejected?

---

**9. RBAC table is incomplete — Cloud Provider Admin and Cloud Infrastructure Admin cannot create system secrets**
- **Category:** Completeness / Scope
- **Severity:** Important
- **Problem:** The RBAC table shows Cloud Infrastructure Admin and Cloud Provider Admin cannot Create. That's correct for self-service secrets. But Workflow 3 requires the operator (running with a service account, not a persona) to call `CreateSecret`. The table does not include a "System / Operator service account" row, leaving implementers uncertain about how the controller authenticates and what policy it needs.
- **Fix:** Add a "System (operator service account)" row to the RBAC table showing full Create permission scoped to system-created secret types (KUBECONFIG, etc.) and document that this account is configured at installation time, not a human persona.

---

### MINOR

---

**10. `SecretReady=True` set synchronously on Create, but no condition lifecycle is defined**
- **Category:** Depth
- **Severity:** Minor
- **Problem:** Workflow 1 step 4 says the DB row is created with `SecretReady=True` immediately. But the Vault write at step 3 could fail (addressed in the failure table), and `SecretReady=False, reason=VaultUnavailable` is mentioned for async failures. There is no initial `SecretReady=Unknown` / `Progressing` state defined, unlike other OSAC resources that use the reconciler pattern. Since Create is synchronous and Vault write precedes DB insert, this is acceptable — but the condition lifecycle should be explicitly stated (no `Unknown` state, `True` or `False` only).
- **Fix:** Add a one-sentence note: "Because `CreateSecret` is synchronous and the Vault write must succeed before the DB row is created, `SecretReady` is never set to `Unknown`; it is `True` on successful creation or the RPC returns an error and no row is written."

---

**11. `DeleteSecret` operation order (Vault delete before or after DB delete) is unspecified**
- **Category:** Depth
- **Severity:** Minor
- **Problem:** Workflow 4 lists steps 3 (Vault delete) and 4 (DB row delete) sequentially, but does not address what happens if step 4 fails after step 3 succeeds. The payload is permanently destroyed but the metadata row remains, causing `GetSecret` to find a row with no corresponding Vault secret. This is the mirror of the create split-brain and should be addressed.
- **Fix:** Specify the order and the failure handling: recommend deleting the DB row first (soft-delete or mark `deleting=true`), then deleting from Vault, then removing the DB row. If Vault delete fails, the DB row is still present and the secret remains accessible — return `UNAVAILABLE` and let the caller retry. Add a row to the failure table for "Vault delete succeeds, DB DELETE fails."

---

**12. `display_name` uniqueness scope is inconsistent between text and DB schema**
- **Category:** Consistency
- **Severity:** Minor
- **Problem:** The unique index `secrets_tenant_name_uidx` is on `(tenant_id, display_name)`, which enforces uniqueness per tenant. The proto comment says "Must be unique within the tenant." Validation in the CRUD table says "display_name unique if changed." All consistent. However, Workflow 3 (operator creating system secrets) uses display_name for idempotency ("idempotent display_name uniqueness") — the failure handling section says "controller reads existing secret instead" on `ALREADY_EXISTS`. This requires the operator to derive a deterministic display_name from the owning resource. This convention is never specified.
- **Fix:** State the naming convention for system-created secrets, e.g., `"system:<resource-type>:<resource-id>:<secret-type>"`. This is necessary for the idempotency claim to hold; without it the operator has no guaranteed deterministic name.

---

**13. `ListSecrets` never returns payload — but this is only stated in implementation notes, not in the proto comment**
- **Category:** Completeness
- **Severity:** Minor
- **Problem:** The payload suppression behavior for `ListSecrets` is documented in Payload Handling but not in the proto definition or `ListSecretsRequest` message. A caller reading only the proto would not know that `include_payload` is not available on List (there's no such field on `ListSecretsRequest`).
- **Fix:** Add a comment to `ListSecretsResponse` or `Secret` (when used in list context): `// payload is always omitted from list responses; use GetSecret with include_payload=true to retrieve payload.`

---

**14. No mention of `osac-aap` integration for system-created secrets beyond the dismissal**
- **Category:** Scope
- **Severity:** Minor
- **Problem:** The Proposal section says "`osac-aap` — no new playbooks required; the operator calls the fulfillment-service API directly. [Assumption]." The PRD states this applies to BMaaS, CaaS, VMaaS, MaaS, Enclave — all of which have provisioning playbooks in `osac-aap`. If a provisioning playbook generates a credential (e.g., an admin password in a BMaaS playbook), the assumption that no AAP changes are needed may be wrong. The design only covers kubeconfig retrieval as an example.
- **Fix:** Enumerate which system-generated secret types are written by the operator (reading from management cluster) vs. which might need to be written by an AAP playbook (e.g., admin passwords generated during OS install). If all are operator-written, state that explicitly and why. If any require AAP changes, flag them.

---

**15. Authors field is `TBD`**
- **Category:** Structure
- **Severity:** Minor
- **Problem:** Standard EP convention requires authors to be identified before document review/approval.
- **Fix:** Fill in the authors field.

---

## Summary Table

| # | Category | Severity | Topic |
|---|----------|----------|-------|
| 1 | Depth/Consistency | Critical | Vault/DB atomicity unresolved without design sketch |
| 2 | Consistency | Critical | UpdateRequest accepts immutable `type` field; no FieldMask |
| 3 | Depth | Critical | SecretBackend interface lacks tenant credential parameter |
| 4 | Depth/Completeness | Important | `vault_path` in status is a security risk, unaddressed |
| 5 | Depth | Important | List pagination semantics unspecified |
| 6 | Consistency | Important | Cross-tenant NOT_FOUND policy absent from error table |
| 7 | Depth/Consistency | Important | Operator Vault auth model breaks tenant isolation claim |
| 8 | Depth | Important | `owner_reference` validation and lifecycle underspecified |
| 9 | Completeness | Important | RBAC table missing operator service account row |
| 10 | Depth | Minor | `SecretReady` condition lifecycle not stated |
| 11 | Depth | Minor | Delete operation order and split-brain not addressed |
| 12 | Consistency | Minor | System-secret display_name naming convention missing |
| 13 | Completeness | Minor | Proto missing comment that List never returns payload |
| 14 | Scope | Minor | `osac-aap` assumption not validated against all secret types |
| 15 | Structure | Minor | Authors field is TBD |