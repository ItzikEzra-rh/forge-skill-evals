## Review: StorageTier API Enhancement Proposal

---

### Overall Assessment

This is an exceptionally well-written design document. It is thorough, internally consistent, and closely tracks the PRD. The proto schemas are complete, workflows are persona-driven, failure modes are exhaustive, and alternatives are honestly evaluated. Issues found are minor-to-important in severity; nothing is critical.

---

## Issues

---

### 1. HTTP response code mismatch in Sequence Diagram

**Category:** Consistency
**Severity:** Important

The Create workflow description (step 5) correctly states `201 HTTP / gRPC OK`. The Mermaid sequence diagram shows `200 OK · StorageTier {id, status.state=ACTIVE}`. REST convention for resource creation is `201 Created`. If the grpc-gateway is configured to return 201, the diagram must match. If the gateway actually returns 200 (some OSAC services do), then step 5 in the workflow text is wrong. Pick one and make them consistent.

**Fix:** Decide what the gateway actually returns and synchronize the workflow text, sequence diagram, and the CRUD table in Implementation Details.

---

### 2. `Update` REST binding sends `body: "object"` but `object.id` is in the URL — `update_mask` and `lock` are unaddressed in the HTTP binding

**Category:** Depth / Proto
**Severity:** Important

The `StorageTiersUpdateRequest` has three fields: `object`, `update_mask`, and `lock`. The HTTP annotation maps `body: "object"`, which means `update_mask` and `lock` are expected as query parameters in the REST binding. This is not stated anywhere in the document. Clients sending a `PATCH` need to know how to pass `lock=true` and `update_mask.paths[]=spec.backends` over REST. The integration test scenario for REST also exercises this ("Optimistic concurrency via REST") without describing how the parameters are actually sent.

**Fix:** Add a note under the proto schema or the REST section specifying that `update_mask` and `lock` are passed as query parameters in the REST binding (or restructure the request so all fields are in the body). Add a concrete example REST call to Workflow 3.

---

### 3. `check_immutable_columns` trigger versus `metadata.name` immutability — dual enforcement gap

**Category:** Consistency
**Severity:** Important

The document claims `metadata.name` immutability is enforced in two places:
1. The Go server `Update` method checks that the name in the request matches the persisted name → returns `INVALID_ARGUMENT`.
2. Migration 75 creates a `check_immutable_columns` DB trigger covering `'id', 'name', 'tenant', 'project'`.

However, the `data` JSONB column stores the serialized proto, which includes `metadata.name`. The `name` column in the table is presumably a materialized scalar for indexing. If the immutable columns trigger guards the `name` column but a direct JSONB update on `data` could change `metadata.name` inside the blob without touching the `name` column, the DB trigger would not catch it. The document does not clarify whether the trigger guards `name` (the table column) or `data->>'metadata'->>'name'` (the JSONB field).

**Fix:** Explicitly state whether `name` in the DB schema is a separate column or extracted from JSONB. If it's a separate column that is always materialized, confirm the trigger protects it. If immutability relies on the Go layer only for the JSONB field, state that explicitly.

---

### 4. `StorageTierState` is missing `DEPRECATED` — but the Non-Goals section and PRD FR-9 are inconsistent about whether this is deferred or permanently excluded

**Category:** Consistency / Scope
**Severity:** Minor

PRD FR-9 explicitly calls out `DEPRECATED` as deferred to a later phase. The design document lists "DEPRECATED state for StorageTier — deferred to a later milestone" in Non-Goals. However, the proto enum `StorageTierState` has no comment reserving field number 2 for `DEPRECATED`. If this state is planned, the proto should include a comment `// STORAGE_TIER_STATE_DEPRECATED = 2; // Reserved for future use` to avoid accidental field number reuse in a v2 update.

**Fix:** Add a reserved comment in the `StorageTierState` enum for the `DEPRECATED` value, or add a `reserved 2;` / `reserved "STORAGE_TIER_STATE_DEPRECATED";` declaration to signal intent.

---

### 5. `BackendAssociation.max_read_bandwidth_mbs` and `max_write_bandwidth_mbs` use `int32` — no sentinel for "unlimited" / unset

**Category:** Depth
**Severity:** Important

The fields `max_read_bandwidth_mbs` and `max_write_bandwidth_mbs` are `int32`. A value of `0` is ambiguous: does it mean "no limit" (unlimited), "not set," or is it invalid? Proto3 uses zero as the default for numeric fields, so an admin who does not set a bandwidth limit will implicitly send `0`. The document does not specify how `0` is interpreted by the server (unlimited? rejected? stored and passed to AAP as `0`?).

The PRD states QoS properties include "maximum read bandwidth (MB/s)" — it does not address the zero/unlimited case. The AAP payload shows concrete non-zero values. This creates an unspecified behavior edge case.

**Fix:** Either (a) change to `optional int32` so unset is distinguishable from zero, or (b) document explicitly that `0` means "no limit enforced" and is stored and passed as-is, or (c) add server validation that rejects `0` as `INVALID_ARGUMENT`. Whichever is chosen, document it in the CRUD spec table and the proto field comment.

---

### 6. JSONB key casing: `backendId` vs `backend_id` — trigger assumes camelCase but proto-to-JSON encoding default behavior is unspecified

**Category:** Depth / Consistency
**Severity:** Important

Migration 76 trigger function reads:
```sql
SELECT jsonb_array_elements(NEW.data->'spec'->'backends')->>'backendId'
```

The proto field is `backend_id` (snake_case). The standard proto JSON encoding converts `backend_id` → `backendId` (camelCase). However, the document does not explicitly state which JSON encoding convention the `GenericDAO` uses when serializing proto to JSONB. If the DAO uses the proto binary format stored as JSONB (unusual but possible), or a non-standard marshaler, the key would be `backend_id` not `backendId`, and the trigger would silently return `NULL` for all backend IDs — meaning the referential integrity check would never fire.

The document notes this risk in the "Risks and Mitigations" section ("JSONB path for trigger extraction must stay in sync") and says the test suite catches mismatches — but only if the test passes a correctly-keyed JSONB. If the JSONB key is wrong from day one, tests would also pass vacuously.

**Fix:** Explicitly state in the migration comment and the trigger function comment that the JSONB encoding uses proto JSON (camelCase) marshaling, and cite the specific marshaler (`protojson.Marshal` or equivalent) used by `GenericDAO`. Add a unit test that directly inspects the JSONB stored in the DB after a `Create` to assert `data->'spec'->'backends'->0->>'backendId'` is non-null.

---

### 7. `Signal` RPC has no HTTP annotation — inconsistency with FR-2

**Category:** Scope / Consistency
**Severity:** Minor

PRD FR-2 states: "All CRUD RPCs must include HTTP annotations for REST access via grpc-gateway." `Signal` is not a CRUD RPC, so technically FR-2 doesn't apply. However, the Goals section says "Register `Signal` RPC to support future OSAC Storage Controller consumption without a service contract change." If Signal is intentionally excluded from REST access, this should be called out explicitly. If it is expected to be callable via REST in the future, a placeholder annotation (returning `UNIMPLEMENTED`) should be included now to reserve the URL.

**Fix:** Add a sentence under the `Signal` RPC definition stating it intentionally has no HTTP annotation because it is infrastructure-only and not callable via REST. Or add a stub annotation to reserve the URL pattern.

---

### 8. `quota_gib` unit inconsistency with PRD NFR-2

**Category:** Consistency / Scope
**Severity:** Important

PRD NFR-2 specifies QoS properties as "quota (integer, **bytes**)." The proto field is named `quota_gib` and typed `int64` (storing GiB). The AAP payload conversion section shows `quota_bytes = quota_gib * 1024³`. This is an explicit naming mismatch with the PRD's stated unit. Either the PRD should have said "quota (GiB)" or the field should be named `quota_bytes` and stored in bytes.

The design document does not acknowledge or justify this deviation from the PRD's unit specification.

**Fix:** Either rename the proto field to `quota_bytes` (and store bytes as the PRD specifies, losing the "petabyte headroom" justification since int64 handles bytes at petabyte scale: 2^63 bytes ≈ 9 exabytes), or explicitly document in the design that GiB was chosen instead of bytes and get PRD sign-off. Either way, add a note cross-referencing NFR-2 and explaining the decision.

---

### 9. Deferred `check_storage_tier_not_in_use` trigger creates an unacknowledged gap in the Delete workflow description

**Category:** Completeness / Depth
**Severity:** Minor

Workflow 4 (Delete a StorageTier) states: "`check_storage_tier_not_in_use` trigger fires (deferred — see note in Failure Handling). Currently returns success." This is slightly misleading — if the trigger doesn't exist yet, it doesn't "fire." The workflow implies a trigger exists but is a no-op, when in fact no trigger is present until OSAC-2872 ships.

More importantly, the CRUD error table for `DeleteStorageTier` lists `"Active Tenant references the tier (deferred trigger, OSAC-23)"` → `FAILED_PRECONDITION (Z0003)`. This is correct for the future state but is not the current behavior. The table should distinguish current behavior (no protection) from future behavior (post-OSAC-2872).

**Fix:** Correct Workflow 4 step 3 to say "No tenant-reference check exists until OSAC-2872 ships; the delete proceeds unconditionally." In the CRUD error table, mark the tenant-reference row clearly as "Not active until OSAC-2872" to avoid implementer confusion.

---

### 10. `osac-operator` file path inconsistency

**Category:** Consistency
**Severity:** Minor

The document references two operator files inconsistently:
- Summary section: `storage_tier_definitions.go`, `storage_tier_resolution.go`
- Cross-Repository table: `osac-operator/internal/controller/storage_tier_definitions.go`, `osac_operator/internal/controller/storage_tier_resolution.go`

The second path uses `osac_operator` (underscore) while the first uses `osac-operator` (hyphen). One is presumably wrong.

**Fix:** Standardize the repository name spelling to match the actual directory name. Verify that the package path `osac-operator/internal/controller/` is correct (Go module paths use hyphens, filesystem directories also use hyphens; underscores would be unusual here).

---

### 11. Open Question 4 (`quota_gib` semantics) is implementation-blocking but treated as advisory

**Category:** Depth
**Severity:** Important

Open Question 4 asks: "Is `quota_gib` a per-tenant quota or a per-tier total capacity declaration?" This is not an advisory question — it directly determines how the OSAC Storage Controller (OSAC-23) uses the field when provisioning tenant storage. If the field means per-tenant quota, it gets passed as a VAST view quota scoped to the tenant. If it means total tier capacity, it's metadata only and OSAC-23 ignores it for per-tenant provisioning.

The AAP payload already converts `quota_gib` to `quota_bytes` and passes it as a VAST view quota — implying a per-tenant semantics — but this is not confirmed. Shipping this field with unresolved semantics creates a risk of API incompatibility between OSAC-1110 and OSAC-23.

**Fix:** Resolve this before marking the design approved. The answer should be in the Implementation Details, not left as an open question. If it is genuinely unresolved, add a blocking note ("Design cannot proceed to implementation until this is resolved") and assign an owner.

---

### Summary Table

| # | Category | Severity | Topic |
|---|----------|----------|-------|
| 1 | Consistency | Important | HTTP 200 vs 201 mismatch between workflow and sequence diagram |
| 2 | Depth | Important | `update_mask`/`lock` not documented as REST query params |
| 3 | Consistency | Important | `check_immutable_columns` trigger scope (column vs JSONB) unclear |
| 4 | Consistency | Minor | No `reserved` declaration for future `DEPRECATED` enum value |
| 5 | Depth | Important | `int32` bandwidth fields: zero value semantics undefined |
| 6 | Depth/Consistency | Important | JSONB key casing (`backendId` vs `backend_id`) not explicitly anchored |
| 7 | Scope/Consistency | Minor | `Signal` RPC intentionally lacks HTTP annotation — not documented |
| 8 | Consistency | Important | `quota_gib` field name contradicts PRD NFR-2 unit spec (bytes) |
| 9 | Completeness | Minor | Delete workflow implies non-existent trigger "fires"; table mixes current/future |
| 10 | Consistency | Minor | `osac-operator` vs `osac_operator` path inconsistency |
| 11 | Depth | Important | `quota_gib` semantics (per-tenant vs per-tier) is implementation-blocking but unresolved |