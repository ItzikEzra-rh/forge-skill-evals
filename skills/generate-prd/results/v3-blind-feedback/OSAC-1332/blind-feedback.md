## PRD Review: OSAC-1332 CaaS Cluster Storage (v0.1)

---

### Issue 1 — Scope: Missing VAST Provider Gaps (Critical)

**Category:** Completeness / Scope

The Jira's Problem Statement identifies a **second major problem**: the existing VAST provider is not CaaS-ready due to three specific gaps — mutable tenant-name storage paths (breaking volumes on rename), overprivileged CSI credentials, and no CaaS provisioning target. The Jira's Definition of Done explicitly requires:

> "VAST provider supports CaaS clusters (tenant-UID paths, RBAC-scoped credentials, hcp_data_plane target)"

The PRD's Problem Statement mentions only the first problem (no storage on CaaS clusters). The VAST provider readiness gap — and its user impact (data loss risk on rename, security exposure from overprivileged credentials) — is entirely absent from both the Problem Statement and In Scope sections.

**Fix:** Add a second paragraph to the Problem Statement describing the VAST provider gaps in terms of user pain (e.g., volumes breaking on tenant rename, credentials granting excess privilege that bypasses QoS controls). Add a corresponding In Scope bullet: "The VAST storage backend is made CaaS-ready — storage paths use tenant UIDs to prevent breakage on rename, CSI credentials are scoped to least-privilege, and a CaaS provisioning target is added."

---

### Issue 2 — Problem Statement: Solution Language (Important)

**Category:** Problem Statement / Design Leakage

The Problem Statement is largely clean, but the phrase "there is no automation to do this after cluster provisioning" leans toward describing the missing solution rather than the user pain. Similarly, "making it impossible to distinguish compute readiness from storage readiness" is acceptable framing, but the overall statement doesn't articulate the **cost of inaction** for the VAST gaps (see Issue 1).

**Fix:** Reframe the automation sentence as a consequence of pain: e.g., "Each cluster requires manual storage setup, creating operational burden and delaying tenant workload availability." Keep focus on what users cannot do or what risk they are exposed to.

---

### Issue 3 — Personas: Tenant Admin and Tenant User Conflated (Important)

**Category:** Personas / Persona Alignment

The PRD groups Tenant Admin and Tenant User into a single combined story. The Jira only has a **Tenant User** story. OSAC conventions require all four personas to be addressed individually. The Jira is silent on Tenant Admin specifically.

The conflated story ("As a Tenant Admin or Tenant User...") is problematic because:
- Self-service PVC creation is a **Tenant User** capability.
- Viewing storage readiness on a cluster is more ambiguous but could reasonably belong to Tenant User as well.
- A Tenant Admin story, if added, needs to reflect org-level configuration, not just PVC creation.

**Fix:** Split into separate entries. Keep the PVC creation and storage readiness visibility stories attributed to **Tenant User** only (matching the Jira). Add a **Tenant Admin** entry that either has a genuine story (e.g., visibility into storage readiness across their org's clusters) or explicitly states "Not affected by this feature." Do not manufacture a story that isn't supported by the Jira.

---

### Issue 4 — Personas: Cloud Infrastructure Admin "Not Affected" Needs Justification (Minor)

**Category:** Personas

Marking Cloud Infrastructure Admin as "Not affected" is acceptable, but the Jira Assumptions state that "A global VIP Pool has been pre-configured by the Cloud Infrastructure Admin." This is a prerequisite action performed by the CIA. The PRD moves this to Assumptions rather than surfacing it as a CIA concern.

The CIA is not entirely absent from this feature's context, and a reader would benefit from understanding why they are not the subject of a user story despite having a setup responsibility.

**Fix:** Either (a) add a CIA user story reflecting their pre-configuration responsibility ("As a Cloud Infrastructure Admin, I want to pre-configure a global VIP Pool so that CaaS clusters have a shared storage connectivity endpoint") if this is genuinely new work in scope, or (b) keep "Not affected" but add a parenthetical clarification: "Not affected — VIP Pool pre-configuration is a prerequisite handled outside this feature's scope."

---

### Issue 5 — Scope: Cleanup on Cluster Deletion Not Prominent Enough (Minor)

**Category:** Completeness

The In Scope section includes "Storage resources on the cluster are cleaned up when the cluster is deleted," which correctly traces to the Jira DoD. However, this is a meaningful lifecycle behavior that affects multiple personas (CPA observes it, tenants are impacted). It is listed as a single bullet without any corresponding user story or async-status consideration (e.g., what does a CPA see during cleanup? Is storage readiness status updated?).

**Fix:** Consider adding a CPA user story: "As a Cloud Provider Admin, I want storage resources to be automatically removed when a CaaS cluster is deleted so that I do not need to manually clean up storage after cluster teardown." This also ensures the async nature of cleanup (status visibility) is addressed per Evaluation Criteria #7.

---

### Issue 6 — Design Leakage: "ClusterOrder CR" in User Stories (Minor)

**Category:** Design Leakage

The CPA story reads: "I want to see storage readiness on a **ClusterOrder** independently from compute readiness." `ClusterOrder` as a platform concept (not an implementation artifact) is acceptable per OSAC conventions. However, the Jira uses "ClusterOrder CR" — the "CR" suffix (Custom Resource) is an implementation term.

The PRD's In Scope bullet uses "ClusterOrder" cleanly (no "CR"). The user story is consistent with that.

**Verdict:** Acceptable as written. No action required — flagging for awareness only.

---

### Summary

| # | Category | Severity | Fix Required |
|---|----------|----------|--------------|
| 1 | Completeness / Scope | Critical | Add VAST provider gap problem + In Scope bullet |
| 2 | Problem Statement | Important | Remove solution framing; describe pain and cost of inaction |
| 3 | Personas | Important | Split Tenant Admin / Tenant User; add explicit Tenant Admin disposition |
| 4 | Personas | Minor | Clarify CIA "Not affected" given their prerequisite role |
| 5 | Completeness | Minor | Add CPA story for cleanup; address async status of deletion |
| 6 | Design Leakage | Advisory | No action needed |

The PRD has a solid foundation but has one critical gap (the VAST provider remediation work is entirely missing from scope and problem statement) and needs persona handling cleaned up before it meets OSAC conventions.