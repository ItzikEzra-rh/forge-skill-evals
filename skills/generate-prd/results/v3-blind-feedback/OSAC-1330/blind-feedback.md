## PRD Review: OSAC-1330 Type-Safe Resource References

---

### Issue 1 — Design Leakage in In Scope

**Category:** design-leakage
**Severity:** critical

**What's wrong:** The In Scope section states: *"References are validated at submission time: invalid references (nonexistent target, inconsistent identifiers) are rejected with descriptive errors before any provisioning begins."* This is acceptable at the capability level. However, the Backwards Compatibility bullet says *"the system auto-populates the missing form when one is provided"* — "auto-populates" is an implementation mechanism (describing the interceptor's behavior of filling in missing fields), not a user-visible capability. Similarly, "both forms are accepted during the transition" is fine, but "auto-populates the missing form" leaks the server-side resolution design from the Jira's Solution section into what should be a problem/capability document.

**Fix:** Reframe as a user-visible outcome: *"During the migration period, clients that provide only an ID or only a name for a referenced resource will receive a valid, consistent response — the API resolves the reference fully without requiring the client to supply both."*

---

### Issue 2 — Design Leakage in Dependencies

**Category:** design-leakage
**Severity:** important

**What's wrong:** The Dependencies section is acceptable in intent but the phrase *"the typed reference format is designed to support both ID-based and name-based identification"* uses design language ("designed to support," "typed reference format"). Dependencies should describe external blockers and relationships, not architectural design choices.

**Fix:** Rewrite to: *"Completion of this feature is coordinated with the broader name-based identification migration. Legacy ID-based references will continue to be accepted until that migration is complete, at which point ID fields may be removed."*

---

### Issue 3 — Missing Scope Item: Server-Side Generic Resolution Interceptor

**Category:** completeness / scope
**Severity:** critical

**What's wrong:** The Jira explicitly scopes *"Implement the generic reference resolution interceptor"* as a deliverable. This is a significant system capability — cross-cutting reference validation and resolution as middleware. The PRD's In Scope mentions validation at submission time but does not call out the cross-cutting/interceptor-as-capability aspect in user-visible terms. More critically, it omits the consistency enforcement requirement: *"if both id and name are provided, they must refer to the same object."* This is a user-visible validation behavior (a user submitting conflicting id+name gets an error) that has no corresponding user story or scope item.

**Fix:** Add a scope item: *"When a request provides both a legacy ID and a name for a referenced resource, the API validates that they refer to the same object and rejects the request with a descriptive error if they are inconsistent."* Add a corresponding user story (likely under Tenant User or Cloud Infrastructure Admin).

---

### Issue 4 — Missing Scope Item: API Documentation and OpenAPI Spec Updates

**Category:** completeness / scope
**Severity:** important

**What's wrong:** The Jira explicitly lists *"Update API documentation and OpenAPI specs"* as in scope. The PRD has no mention of documentation or specification updates. This is a user-facing deliverable — API consumers need updated specs to adopt the new reference types.

**Fix:** Add to In Scope: *"API documentation and OpenAPI specifications are updated to reflect the new reference message types, replacing documentation of raw string fields."*

---

### Issue 5 — Missing Scope Item: Test Coverage

**Category:** completeness / scope
**Severity:** minor

**What's wrong:** The Jira scopes *"Update tests to cover reference validation and resolution."* PRDs generally do not enumerate test requirements (testing is implied), so omitting this is acceptable by OSAC convention. However, if the team uses the PRD to drive acceptance, the absence is notable.

**Fix:** No action required — test updates are an implementation concern, not a PRD-level scope item under OSAC conventions.

---

### Issue 6 — Problem Statement Contains Mild Solution Language

**Category:** problem-statement
**Severity:** important

**What's wrong:** The final sentence of the Problem Statement reads: *"the lack of structured references makes it impossible to evolve reference fields without breaking every consumer."* The phrase "structured references" implies the solution concept (structured/typed references) rather than describing the pain neutrally. The statement also contains *"leaving cross-tenant reference semantics undocumented and inconsistently enforced"* which is fine — that is pure pain. But "impossible to evolve reference fields" is borderline acceptable; "lack of structured references" is not — it names the solution's absence rather than the problem itself.

**Fix:** Rewrite the final sentence as: *"As OSAC migrates from ID-based to name-based identification, reference fields cannot evolve without breaking every existing API consumer, making the migration path unmanageable."*

---

### Issue 7 — Persona Alignment: Cloud Infrastructure Admin Story Is Weak

**Category:** personas / persona-alignment
**Severity:** important

**What's wrong:** The Cloud Infrastructure Admin story focuses on *"reference nonexistent resources (e.g., a network class or IP pool that does not exist)"* — this is a valid CIA concern. However, the CIA's primary concern in this feature context is managing the infrastructure-level resources that *are referenced* (networks, IP pools, network classes) and ensuring operators managing these get clear feedback when references are misconfigured across services. The story as written is nearly identical to the Tenant User validation story, differing only in the example resources named. The CIA story should reflect the admin's cross-service or infrastructure-management perspective, not just submission-time validation (which any user cares about).

**Fix:** Reframe: *"As a Cloud Infrastructure Admin, I want to be able to audit which resources are referenced by which other resources across tenants so that I can safely modify or retire infrastructure resources without causing silent failures."* Alternatively, align the existing story more explicitly to the CIA's cross-service operational concern rather than echoing the Tenant User story.

---

### Issue 8 — Assumptions Section Missing Transition Endpoint Assumption

**Category:** completeness
**Severity:** minor

**What's wrong:** The Assumptions state that OSAC does not support in-place upgrades, so clients adopt the new format at redeployment. This is correct and useful. However, there is no assumption about *when* legacy ID fields will be removed — the PRD implies they persist indefinitely until the name-based migration completes, but does not state this as an assumption. Given that the Jira explicitly marks the ID field as "to be removed after migration," the PRD should acknowledge that the removal timeline is outside this feature's scope and depends on a separate decision.

**Fix:** Add assumption: *"The removal of legacy ID fields from reference messages is out of scope for this feature and will be decided as part of the name-based identification migration effort."*

---

### Issue 9 — Template Compliance: Sections Are Correct

**Category:** template
**Severity:** (no issue)

The PRD contains exactly the permitted sections: Problem Statement, In Scope, Out of Scope, User Stories, Assumptions, Dependencies. No extra sections (Risks, Acceptance Criteria, etc.) are present. ✅

---

### Issue 10 — Async Status: Not Applicable

**Category:** (no issue)

This feature involves API schema changes and synchronous submission-time validation. There is no asynchronous resource creation lifecycle introduced. No async status coverage is needed. ✅

---

## Summary Table

| # | Category | Severity | Description |
|---|----------|----------|-------------|
| 1 | design-leakage | critical | "Auto-populates" in In Scope leaks implementation mechanism |
| 2 | design-leakage | important | Dependencies uses design language ("typed reference format is designed to") |
| 3 | completeness/scope | critical | Missing scope item and user story for id+name consistency enforcement |
| 4 | completeness/scope | important | Missing scope item for API documentation / OpenAPI spec updates |
| 5 | completeness/scope | minor | Test updates omitted (acceptable per OSAC convention) |
| 6 | problem-statement | important | "Lack of structured references" names the solution's absence, not the problem |
| 7 | persona-alignment | important | CIA story duplicates Tenant User story; should reflect cross-service admin concern |
| 8 | completeness | minor | No assumption about when/how legacy ID fields will eventually be removed |