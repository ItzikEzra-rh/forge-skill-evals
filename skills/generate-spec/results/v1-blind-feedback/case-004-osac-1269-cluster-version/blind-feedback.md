## Design Document Review: `cluster-version-api`

---

### Overall Assessment

This is an exceptionally thorough design document. The proto schemas, workflows, failure table, RBAC table, and test plan are all substantive and specific. Most OSAC conventions are followed correctly. The issues below are real gaps, not nitpicks.

---

## Issues Found

---

### 1. `spec.version` Field Naming Inconsistency (Proto vs. UX Table vs. CLI)

**Category:** Consistency
**Severity:** Important

**Problem:** The UX alignment table maps `spec.versionName` (TypeScript) to `spec.version` (proto). The proto field is named `version` (the human-readable SemVer string, e.g., `"4.17.0"`). The `metadata.name` field (e.g., `"4-17-0"`) is what gets stored in `ClusterSpec.version_name`. But in the CLI section, `osac create cluster --version 4.17.0` is documented to accept both `"4.17.0"` (the `spec.version` SemVer string) and `"4-17-0"` (the `metadata.name`). The resolution logic for this ambiguity is never specified: when the user passes `--version 4.17.0`, does the CLI look up by `spec.version` or by `metadata.name`? And what does the fulfillment-service `CreateCluster` actually accept in `ClusterSpec.version_name`?

The document says `version_name` "references `ClusterVersion.metadata.name`" (e.g., `"4-17-0"`), but if `GetClusterVersion` takes `id_or_name` that resolves either, and the CLI passes through the raw user input, then the full lookup path is underspecified.

**Fix:** Explicitly state what `ClusterSpec.version_name` accepts (only `metadata.name` form, only `spec.version` form, or either via a server-side lookup), how `GetClusterVersion(id_or_name)` resolves ambiguity between a SemVer string and a dash-normalized name, and how the CLI translates `--version 4.17.0` into the proto field value.

---

### 2. `allowed_upgrades` Cleanup on Target Deletion is Open but Also Described as "Auto-Cleaned"

**Category:** Consistency
**Severity:** Important

**Problem:** Open Question 4 asks how `allowed_upgrades.version_names` entries are cleaned up when a referenced version is deleted. But the delete-protection trigger (Trigger 2) checks `clusters`, `cluster_templates`, and `cluster_catalog_items` — it does not mention `allowed_upgrades` cross-references. If Version A lists Version B in its `allowed_upgrades.version_names`, and Version B is deleted, the trigger does not block the deletion (B is not "referenced by" A in the protected tables). The Risks section doesn't cover stale `allowed_upgrades` entries. The Failure Handling table doesn't cover this scenario. Yet elsewhere the text says entries are "auto-cleaned" as if it's settled.

**Fix:** Resolve this before publication. Either: (a) extend the delete-protection trigger to also block deletion when the version is named in another version's `allowed_upgrades`; (b) add a DB trigger on soft-delete to cascade-clean `allowed_upgrades` references; or (c) explicitly document that stale names in `allowed_upgrades` are ignored (and add a unit test for that behavior). Remove the phrase "auto-cleaned" unless the mechanism is specified.

---

### 3. `ClusterVersionStatus` is Empty — No `conditions` Field

**Category:** Depth / Scope
**Severity:** Important

**Problem:** The proto defines `message ClusterVersionStatus {}` with a comment "Reserved for future conditions." But the controller adds a `VersionNotFound` condition to the *Cluster* status, not to the `ClusterVersion` status. Several other places in the document reference non-fatal `VersionDeprecated` status conditions (Workflow 5). The status message should at minimum include a `repeated Condition conditions` field following the standard OSAC object shape, even if it starts empty. Leaving it truly empty means the field cannot be added later without a proto field number assignment, and the "reserved for future" claim is not backed by any reserved field numbers.

**Fix:** Add a `repeated Condition conditions = 1;` field to `ClusterVersionStatus` (using the existing OSAC `Condition` type), or add reserved field numbers if conditions are genuinely deferred. Clarify that `VersionDeprecated` is a condition on the `Cluster` status (not `ClusterVersion` status) and document its proto field number.

---

### 4. Public/Private API Split Mechanism is Unresolved but Load-Bearing

**Category:** Depth
**Severity:** Important

**Problem:** The document repeatedly defers the `spec.image` projection mechanism to "confirm during implementation" (Open Question 2, Implementation Details, Security Considerations). This is not a minor detail — it is the core security property of the entire feature. The failure mode ("`spec.image` appearing in public API response (security incident)") is listed as a risk with only an integration test as mitigation. For an implementer, "field mask applied at serialization vs. DAO-level projection" left open means the implementation could go either way, and one of those ways may not be safe.

**Fix:** Make a decision in this document. If the existing projection mechanism handles it, name the mechanism and the extension point (e.g., "add `image` to the `privateOnlyFields` list in `ClusterVersionServer.ToPublicResponse()`"). If a new mechanism is needed, specify it. The integration test is necessary but not sufficient as the only safeguard — the architectural decision must be settled here.

---

### 5. `ClusterSpec.release_image` Field Reservation is Incorrect in the Proto Snippet

**Category:** Consistency / Depth
**Severity:** Important

**Problem:** The proto snippet comments out the field and shows `// reserved 6; // reserved "release_image";` but these are comments, not actual proto `reserved` statements. In proto3, omitting the `reserved` declaration means field number 6 could accidentally be reused in the future. The Drawbacks section correctly says "the field must be reserved rather than reused," but the proto snippet doesn't actually do it.

**Fix:** Replace the commented-out lines with actual proto reserved declarations:
```protobuf
reserved 6;
reserved "release_image";
```

---

### 6. `osac create cluster --version` Accepts Both Forms — Lookup Semantics Missing from Server

**Category:** Depth
**Severity:** Important

**Problem:** The CLI section documents:
> "Also accepts metadata.name form: `osac create cluster --version 4-17-0`"

But `ClusterSpec.version_name` is documented as referencing `ClusterVersion.metadata.name`. If the user passes `"4.17.0"` (SemVer with dots), the CLI must either (a) transform it to `"4-17-0"` client-side using the auto-generation algorithm, or (b) the server must accept both forms in `ClusterSpec.version_name`. Neither is specified. The auto-generation algorithm has collision-handling (hex suffix) that cannot be reproduced client-side without knowing the actual stored name.

**Fix:** Specify whether `ClusterSpec.version_name` accepts `spec.version` strings (dots), `metadata.name` strings (dashes), or both, and where the normalization occurs (CLI, gateway, or server). Recommendation: accept only `metadata.name` in the proto field; have the CLI resolve `"4.17.0"` → `"4-17-0"` by calling `ListClusterVersions` filtered by `spec.version = "4.17.0"` and extracting `metadata.name`.

---

### 7. Workflow 5 — Deprecation Warning Mechanism Deferred but Not Tracked

**Category:** Completeness
**Severity:** Important

**Problem:** Workflow 5 ends with "[Assumption: warning surfaced via metadata annotation; exact mechanism to be confirmed during implementation]." Open Question 1 repeats this. The acceptance criteria in the PRD requires: "Deprecated versions allow creation; the deprecation is surfaced to the user." This is an acceptance criterion, not a nice-to-have. Leaving the mechanism entirely open means there is no implementation contract and no test can be written against it. The test plan lists "Deprecated version warning" as an E2E test but gives no detail on what to assert.

**Fix:** Decide on the warning mechanism before publication. If gRPC response trailers are used, document the trailer key and value format. If a `ClusterStatus` condition is used, document the condition type and message. Update the E2E test to assert the specific observable behavior.

---

### 8. `ListClusterVersionsRequest` Omits Pagination Fields

**Category:** Depth / Completeness
**Severity:** Minor

**Problem:** The proto comment says "Standard pagination fields omitted for brevity; follow existing List patterns." OSAC convention is to include the actual pagination fields in the design document proto, not defer them. Other OSAC EPs that introduce new List RPCs include `page_token`, `page_size`, and `order_by` with field numbers assigned. Omitting them here means field numbers must be assigned later, creating a risk of conflict.

**Fix:** Add pagination fields to `ListClusterVersionsRequest` with explicit field numbers:
```protobuf
int32 page_size = 2;
string page_token = 3;
string order_by = 4;
```
And add `string next_page_token = 2;` to `ListClusterVersionsResponse`.

---

### 9. Inbound Reference Trigger Validates `enabled = true` — But `DEPRECATED` Versions Are Allowed

**Category:** Consistency
**Severity:** Minor

**Problem:** Trigger 3 (inbound reference validation) checks `enabled = true` and `state != OBSOLETE`. But the document says `DEPRECATED` versions are allowed for new cluster creation (Workflow 5, FR-7). This is consistent. However, there is no mention of what happens when a version is `enabled = false` but not `OBSOLETE`. The `enabled` flag appears to block new cluster creation (the trigger rejects it), but this is not stated in the PRD and is not covered in the Failure Handling table. Conversely, Workflow 4 validates "not OBSOLETE, enabled=true" — but it's in the server code path, not the trigger. There is a potential double-enforcement here, and the semantics of `enabled=false` on a `DEPRECATED` version are not defined.

**Fix:** Add a row to the Failure Handling table for "`CreateCluster` with `enabled=false` version." Clarify whether `enabled=false` is a user-visible concept or an admin-only maintenance flag, and whether it is a separate gate from `OBSOLETE` or subsumed by it. Clarify whether the trigger or the server-layer validates `enabled`, or both.

---

### 10. No Migration Path Specified for `ClusterTemplateSpecDefaults.version_name`

**Category:** Scope / Completeness
**Severity:** Minor

**Problem:** The document correctly notes that the PRD assumes "No production catalog items exist that reference the release image." The Upgrade/Downgrade Strategy covers `ClusterSpec` migration but does not address `ClusterTemplateSpecDefaults`. If templates exist with a `release_image` analog in their defaults, the migration for templates is the same problem as for clusters, but it is not mentioned. The delete-protection trigger checks `cluster_templates` for version references — so templates are a first-class concern.

**Fix:** Add a sentence to the Upgrade/Downgrade Strategy section stating how existing `ClusterTemplateSpecDefaults` records are handled (either "none exist per PRD assumption 5.2" — cite it explicitly — or describe the migration).

---

### 11. `ClusterVersionState_UNSPECIFIED` Handling in `ListClusterVersionsRequest.states` Filter

**Category:** Depth
**Severity:** Minor

**Problem:** The `states` filter in `ListClusterVersionsRequest` says "if absent, returns ACTIVE and DEPRECATED." But what happens if a caller passes `CLUSTER_VERSION_STATE_UNSPECIFIED` in the list? This is a common proto pitfall where zero-value enums sneak into repeated fields. The behavior should be defined (ignore it, treat as error, or treat as "all states").

**Fix:** Add a sentence: "UNSPECIFIED in the `states` list is ignored. Passing only UNSPECIFIED is equivalent to omitting the field."

---

### 12. `osac describe cluster` — Second gRPC Call Latency and Failure Behavior

**Category:** Depth
**Severity:** Minor

**Problem:** The CLI section says "`osac describe cluster <name>` fetches `ClusterVersion` in a second gRPC call; renders version string, state, deprecation/obsolescence timestamps." There is no specification of what the CLI renders if that second call fails (e.g., the version has been deleted, or the service is unavailable). Given that delete protection prevents deletion of in-use versions, this should rarely happen, but the CLI UX for the failure case is unspecified.

**Fix:** Add a note: "If `GetClusterVersion` returns `NOT_FOUND` or an error, `describe cluster` renders `version_name: <name> (state: unknown — version not found)` and does not fail the overall command."

---

### Summary Table

| # | Category | Severity | Issue |
|---|----------|----------|-------|
| 1 | Consistency | Important | `version_name` field accepts SemVer vs. dash-form — lookup path undefined |
| 2 | Consistency | Important | `allowed_upgrades` cleanup on deletion unresolved but described as settled |
| 3 | Depth | Important | `ClusterVersionStatus` empty with no reserved fields; `VersionDeprecated` condition undeclared |
| 4 | Depth | Important | `spec.image` public/private projection mechanism deferred but load-bearing security property |
| 5 | Consistency | Important | Proto snippet uses commented-out `reserved` instead of actual `reserved` declarations |
| 6 | Depth | Important | CLI `--version` accepts both forms; server normalization path unspecified |
| 7 | Completeness | Important | Deprecation warning mechanism entirely deferred with no fallback contract |
| 8 | Completeness | Minor | `ListClusterVersionsRequest` missing pagination fields and field numbers |
| 9 | Consistency | Minor | `enabled=false` gate behavior undefined; potential double-enforcement with trigger |
| 10 | Completeness | Minor | Template migration path omitted from Upgrade/Downgrade Strategy |
| 11 | Depth | Minor | `CLUSTER_VERSION_STATE_UNSPECIFIED` in `states` filter behavior undefined |
| 12 | Depth | Minor | `osac describe cluster` second-call failure UX unspecified |

---

### What is Solid

The document does the following exceptionally well and should not be changed:

- **Failure Handling table** — concrete, named, covers both happy and sad paths with specific SQLSTATE codes, gRPC codes, and user-visible messages.
- **RBAC table** — complete, covers all three personas against all five operations including the public/private split.
- **Alternatives section** — all three alternatives have honest rejection rationale tied to specific PRD requirements.
- **DB trigger specification** — trigger purpose, event (`BEFORE UPDATE/INSERT`), tables affected, and SQLSTATE raised are all named. This is implementer-ready.
- **Workflow sequences** — the mermaid diagram in Workflow 4 is accurate and traces the full call path. Workflow 3's transition table is correct and matches FR-13.
- **Test plan specificity** — test cases name the exact assertion (e.g., "assert `spec.image` is empty string in public `GetClusterVersion` response"), not generic categories.
- **`translateError` gap** — calling this out explicitly with the SQLSTATE-to-gRPC mapping table and noting it must land before trigger-dependent E2E tests is excellent operational awareness.