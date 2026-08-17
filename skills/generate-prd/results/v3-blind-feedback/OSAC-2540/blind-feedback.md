## PRD Review: OSAC-2540 DiskImage Resource

### Overall Assessment

The PRD is well-structured and covers the Jira faithfully. Most issues are minor. A few items need attention.

---

### Issues Found

---

**Issue 1**
- **Category:** Problem Statement
- **Severity:** Important
- **Finding:** The problem statement contains solution language. The phrase "replacing inline image fields on ComputeInstance and ComputeInstanceTemplate" describes the solution, not the pain. Similarly, "no structured surface to curate, deprecate, or retire images" leans toward describing an absent solution rather than a user cost.
- **Fix:** Remove "replacing inline image fields on ComputeInstance and ComputeInstanceTemplate" entirely from the problem statement — that belongs in In Scope. Rephrase the governance sentence to describe the consequence of the gap (e.g., "Cloud Provider Admins and Tenant Admins have no way to control which images are available to tenants, prevent use of outdated images, or signal to users that an image is being retired") without implying a specific solution surface.

---

**Issue 2**
- **Category:** Completeness
- **Severity:** Important
- **Finding:** The Jira DoD explicitly calls out: *"Proto `is_windows` (bool) replaced by `guest_os_family` (enum: linux, windows) on DiskImage"* and *"Inline image fields (`source_type`, `source_ref`, `is_windows`) removed from ComputeInstance and ComputeInstanceTemplate."* These are meaningful scope commitments (breaking API changes) but are absent from In Scope. They appear only implicitly through the Assumptions section mentioning the enum replacement. A reader of the PRD alone would not know that existing inline fields on ComputeInstance and ComputeInstanceTemplate are being removed.
- **Fix:** Add an explicit In Scope bullet: "Removal of inline image fields (`source_type`, `source_ref`, `is_windows`) from ComputeInstance and ComputeInstanceTemplate, replaced by a DiskImage reference." Move or expand the `is_windows` → `guest_os_family` migration into In Scope rather than burying it in Assumptions.

---

**Issue 3**
- **Category:** Completeness
- **Severity:** Important
- **Finding:** The Jira DoD includes *"API reference documentation"* and *"Tests added and passing"* as explicit DoD items. While PRDs do not need to list test requirements, API documentation is a deliverable that affects scope and can affect other teams (developer experience, support). It is absent from In Scope.
- **Fix:** Add an In Scope bullet for API reference documentation as a required deliverable of this feature. Tests can remain omitted from the PRD (that is an engineering concern).

---

**Issue 4**
- **Category:** Completeness
- **Severity:** Important
- **Finding:** No user story addresses the Tenant User's (or any persona's) ability to see the lifecycle state of an image **on their existing ComputeInstance** — i.e., discovering that an image they already launched with has been deprecated or made obsolete. This is mentioned in In Scope ("Users can see the lifecycle state of an image referenced by their ComputeInstance") but has no corresponding user story for any persona.
- **Fix:** Add a Tenant User story: "As a Tenant User, I want to see the lifecycle state of the DiskImage referenced by my existing ComputeInstance so that I know when an image I am using has been deprecated or marked obsolete."

---

**Issue 5**
- **Category:** Design Leakage
- **Severity:** Minor
- **Finding:** The Assumptions section uses the term "proto is_windows (bool)" indirectly through the phrase "replacing the per-instance boolean that exists today." Actually it says "replacing the per-instance boolean" — this is acceptable. However, the In Scope bullet reads "replacing inline image fields on ComputeInstance and ComputeInstanceTemplate" which references internal API field names (`source_type`, `source_ref`) implicitly through the problem statement. In the Assumptions section, the phrase "replacing the per-instance boolean that exists today" is borderline but acceptable as it describes current user behavior. No critical leakage detected here — flag as minor for awareness.
- **Fix:** No change required, but if internal field names are added to In Scope per Issue 2, keep them at the level of "inline image fields" rather than enumerating proto field names.

---

**Issue 6**
- **Category:** Scope
- **Severity:** Minor
- **Finding:** The Out of Scope item "Image binary upload through OSAC — DiskImages wrap existing OCI artifact references only" is fine, but the Jira also explicitly lists *"Image caching or performance optimization"* and *"VM snapshot/export"* as out of scope. These are omitted from the PRD's Out of Scope section. While not every Jira OOS item must appear, snapshot/export is meaningfully adjacent and its absence could cause scope confusion during implementation.
- **Fix:** Add "VM snapshot or image export" and "Image caching or performance optimization" to Out of Scope for completeness and to prevent scope creep conversations.

---

**Issue 7**
- **Category:** Template
- **Severity:** Minor
- **Finding:** The PRD has exactly six sections (Problem Statement, In Scope, Out of Scope, User Stories, Assumptions, Dependencies), which conforms to the OSAC template. The header table (Author, Jira, Date) is standard. No extra sections present. ✓ No issue.

---

**Issue 8**
- **Category:** Personas
- **Severity:** Minor
- **Finding:** All four personas are addressed. Cloud Infrastructure Admin has an explicit "Not affected" note consistent with the Jira. ✓ No issue.

---

**Issue 9**
- **Category:** Async Status
- **Severity:** Minor
- **Finding:** DiskImage creation wraps an OCI artifact reference. There is no indication the feature involves asynchronous provisioning (no image pulling, no long-running operations described). The lifecycle state changes (deprecate, obsolete, reactivate) appear to be synchronous administrative actions. No async gap detected, but if image validation against the OCI registry is performed at create time and could be async, this should be addressed.
- **Fix:** If image reference validation is async (e.g., the system checks the OCI registry after creation and the DiskImage enters a "validating" state), add a user story for observing validation status. If validation is synchronous or deferred, no change needed. Recommend the team confirm this during refinement.

---

### Summary Table

| # | Category | Severity | One-line summary |
|---|----------|----------|-----------------|
| 1 | Problem Statement | Important | Solution language ("replacing inline image fields") in problem statement |
| 2 | Completeness | Important | Removal of inline fields from ComputeInstance/Template not in In Scope |
| 3 | Completeness | Important | API reference documentation missing from In Scope |
| 4 | Completeness | Important | No user story for lifecycle state visibility on existing ComputeInstances |
| 5 | Design Leakage | Minor | Watch internal field name exposure if Issue 2 fix is applied |
| 6 | Scope | Minor | OOS missing "VM snapshot/export" and "image caching" from Jira |
| 9 | Async Status | Minor | Async image validation scenario not assessed — confirm during refinement |