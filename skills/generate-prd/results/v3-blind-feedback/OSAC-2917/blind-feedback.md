## PRD Review: OSAC-2917 GPU-Enabled InstanceTypes for ComputeInstances (MVP)

---

### Issue 1 — Scope: Missing Out-of-Scope Item

**Category:** Scope
**Severity:** Important

**What's wrong:** The Jira explicitly lists "GPU clusters with InfiniBand interconnect" as deferred to OSAC-1839. The PRD's Out of Scope section omits this item entirely.

**Fix:** Add "GPU clusters with InfiniBand interconnect — deferred to OSAC-1839" to the Out of Scope section.

---

### Issue 2 — Scope: Out-of-Scope Deferrals Incorrectly Point to OSAC-1839

**Category:** Scope
**Severity:** Important

**What's wrong:** Several Out of Scope items (per-tenant GPU quotas, MIG/vGPU, GPU VM live migration, GPU-compatible boot image filtering, multi-cluster GPU placement, GPU type validation, cost estimation/billing) are tagged as "deferred to OSAC-1839" in the PRD. However, OSAC-1839 is described in the Jira's linked issues as "GPU-Enabled Compute Instances for Multitenant Environments" — a parallel in-progress feature, not a future catch-all bucket. The PRD should not characterize OSAC-1839 as the destination for deferred work without basis; the Jira simply lists these items as "out of scope" and cites OSAC-1839 as a linked issue. Misrepresenting the relationship could mislead stakeholders.

**Fix:** Remove the blanket "deferred to OSAC-1839" attribution from each Out of Scope line unless that linkage is explicitly confirmed. Replace with neutral language such as "not in scope for this MVP" or simply omit the attribution where it is speculative.

---

### Issue 3 — Problem Statement: Contains Solution Language

**Category:** Problem Statement
**Severity:** Important

**What's wrong:** The final sentence — *"Without GPU support, tenants must provision GPU workloads outside OSAC, bypassing tenant isolation and self-service workflows that the platform provides for CPU-based VMs"* — begins as cost-of-inaction but ends by implicitly describing what OSAC's CPU-based system already provides ("the platform provides for CPU-based VMs"), which edges toward describing the solution space. More critically, the opening of the Problem Statement says *"The InstanceType resource only models CPU cores, memory, and disk — there is no mechanism to express GPU requirements"* — this is acceptable pain description — but the PRD adds *"bypassing tenant isolation and self-service workflows that the platform provides"* which implies a solution (restoring those workflows via this feature).

**Fix:** Tighten the final sentence to focus purely on user pain and business risk, e.g.: *"As a result, tenants running AI/ML workloads must provision GPU infrastructure outside OSAC, operating without the tenant isolation and governance controls that apply to other workloads on the platform."*

---

### Issue 4 — Completeness: Missing User Story for Cloud Provider Admin Delete

**Category:** Completeness
**Severity:** Minor

**What's wrong:** The Jira's Definition of Done explicitly includes *"Cloud Provider Admin can create, update, and delete GPU-enabled InstanceTypes."* The PRD's Cloud Provider Admin stories cover create (define) and update/retire, but do not explicitly surface **delete** as a distinct user story or capability. "Retire" is ambiguous — it could mean soft-deprecation, not deletion.

**Fix:** Either add a discrete user story — *"As a Cloud Provider Admin, I want to delete GPU-enabled InstanceTypes that are no longer available so that tenants cannot select hardware that no longer exists"* — or clarify within the existing retire/update story that deletion is included and what it means operationally.

---

### Issue 5 — Completeness: Async Status Story Scope Is Narrow

**Category:** Completeness / Async Status
**Severity:** Minor

**What's wrong:** The PRD addresses async status visibility with the Tenant User story: *"I want to see the current provisioning status and any failure reasons for my GPU-enabled ComputeInstance."* This is good. However, this story is absent from the Jira's explicit user stories, and the Jira's DoD does not call it out either — meaning the PRD adds it, which is fine per OSAC conventions for async flows. But the In Scope bullet that covers it (*"Tenant Users can see the current provisioning status and any failure reasons"*) is redundant with the user story and slightly verbose for an In Scope line.

**No action required** — the PRD correctly adds the async visibility story per OSAC convention. The redundancy between the In Scope bullet and the user story is acceptable. Flagged for awareness only.

---

### Issue 6 — Template: No Extra Sections Present — Compliant

**Category:** Template
**Severity:** N/A (no issue)

The PRD contains exactly the permitted sections: Problem Statement, In Scope, Out of Scope, User Stories, Assumptions, Dependencies. No prohibited sections (Risks, Acceptance Criteria, Metrics, etc.) are present. Compliant.

---

### Issue 7 — Personas: All Four Addressed — Compliant

**Category:** Personas
**Severity:** N/A (no issue)

Cloud Provider Admin, Cloud Infrastructure Admin, Tenant Admin, and Tenant User are all addressed. CIA and Tenant Admin carry explicit "Not affected" notes. Compliant.

---

### Issue 8 — Design Leakage: Assumption References Ansible/AAP Implicitly via OSAC-42

**Category:** Design-leakage
**Severity:** Minor

**What's wrong:** The Assumptions section states *"GPU passthrough via KubeVirt is functional"* — KubeVirt is platform vocabulary and acceptable. However, the Dependencies section describes OSAC-42 as *"Provides the infrastructure-level GPU passthrough capability"* without mentioning Ansible/AAP (which the Jira calls out: "Ansible-level GPU passthrough plumbing already delivered in osac-aap"). This is actually better than the Jira — the PRD correctly avoids leaking the Ansible/AAP implementation detail. No fix needed here; the PRD handles this correctly.

---

## Summary

| # | Category | Severity | One-line Summary |
|---|----------|----------|-----------------|
| 1 | Scope | Important | InfiniBand interconnect out-of-scope item missing |
| 2 | Scope | Important | Blanket "deferred to OSAC-1839" attribution is unsupported and potentially misleading |
| 3 | Problem Statement | Important | Final sentence drifts into solution language |
| 4 | Completeness | Minor | Cloud Provider Admin delete capability not explicitly surfaced in user stories |

Issues 5–8 are non-blocking observations. The PRD is otherwise well-structured, avoids design leakage, correctly handles async status, and maps cleanly to the Jira scope.