## PRD Review: OSAC-2872 Storage Control Plane

---

### Issue 1 — Design Leakage in Problem Statement
**Category:** design-leakage
**Severity:** important

The sentence *"There is no enforcement point for per-tenant storage policy"* is borderline acceptable (describes absence of capability), but *"vendor credentials must be stored on tenant clusters"* is describing a current architectural constraint/implementation detail rather than user pain. More clearly, the phrase *"no central record of what volumes exist"* is acceptable. However, the overall Problem Statement is clean enough on most sentences.

The real leakage is in **In Scope**: *"Cross-cluster authentication between the tenant cluster and the storage control plane"* — "cross-cluster authentication" is an implementation/design mechanism, not a capability. The PRD should say something like *"Storage on tenant clusters is secured such that only authorized clusters can request volume operations from the platform"* — i.e., the outcome, not the mechanism.

**Fix:** Replace "cross-cluster authentication between the tenant cluster and the storage control plane" with outcome language: *"Storage provisioning on tenant clusters is secured so that only the authorized cluster can initiate volume operations on behalf of its tenants."*

---

### Issue 2 — Design Leakage in In Scope (CSI internals)
**Category:** design-leakage
**Severity:** important

*"Multiple storage vendors (NetApp ONTAP, VAST, Pure Storage) are supported behind a single CSI interface on each tenant cluster"* — "CSI interface" is an implementation detail (CSI is a Kubernetes spec/driver protocol). The PRD should describe this as the capability: tenants see a single, uniform storage interface regardless of which vendor backs it.

Similarly, *"Vendor credentials are provided per-request"* — "per-request" is an implementation detail about credential delivery timing/pattern, not a user-facing capability. The user-facing capability is that vendor credentials are never accessible to tenant clusters.

**Fix:**
- Replace "behind a single CSI interface" → "through a single, uniform storage interface"
- Replace "provided per-request and are never stored on tenant clusters" → "are never stored on or accessible from tenant clusters"

---

### Issue 3 — Design Leakage in User Stories (Tenant User)
**Category:** design-leakage
**Severity:** important

*"I want to create a PVC using a StorageClass on my CaaS cluster"* — PVC (PersistentVolumeClaim) and StorageClass are Kubernetes implementation objects. The PRD should describe the user action in terms of what the user wants to accomplish, not the Kubernetes API objects they interact with.

**Fix:** Rephrase: *"As a Tenant User, I want to request persistent storage for my workload using my cluster's available storage tiers so that my workload has durable storage without needing to know the underlying vendor or backend."*

---

### Issue 4 — Missing Capability: Storage Readiness / Status Visibility
**Category:** completeness
**Severity:** important

The Jira has a clear in-scope item for observability of storage readiness, and the PRD In Scope item covers it: *"Tenants and admins can see whether storage is ready on a given cluster."* However, the User Stories only partially address this:

- **Tenant Admin** has no story about checking storage readiness — only about seeing available tiers.
- **Cloud Infrastructure Admin** has no story about verifying storage deployment status on a specific cluster (only CPA does).
- The Tenant User story for status visibility is present.

The Jira's automated deployment story implies the CIA is the one who configures and verifies deployment, yet the PRD assigns the readiness-check story only to CPA. The CIA should also have a readiness story since they're responsible for provisioning.

**Fix:** Add a CIA user story: *"As a Cloud Infrastructure Admin, I want to verify that storage is successfully deployed and ready on any tenant cluster so that I can confirm provisioning completed correctly before tenants use it."*

---

### Issue 5 — Assumptions Section Missing a Key Assumption
**Category:** completeness
**Severity:** minor

The Jira's CSI driver core story notes: *"Vendor CSI node plugins are available on tenant clusters for mount operations."* The PRD captures this in Assumptions. However, there is a missing assumption: the hub cluster network must be reachable from tenant cluster CSI drivers (for the control plane proxy pattern). This is implied by the architecture but not stated.

Additionally, the assumption *"At least one storage vendor... has been configured by a Cloud Infrastructure Admin before tenants can provision volumes"* is good, but the PRD doesn't state the assumption that tenant clusters are OCP/Kubernetes clusters with kubelet and standard CSI sidecar support — which is a prerequisite the Jira implicitly assumes throughout.

**Fix:** Add: *"Tenant clusters run OpenShift/Kubernetes with standard CSI sidecar support (external-provisioner, external-attacher)."* and *"The storage control plane on the hub cluster is network-reachable from tenant cluster nodes."*

---

### Issue 6 — Private Volume API Missing from In Scope
**Category:** completeness / scope
**Severity:** important

The Jira has a distinct, independently demoable story for **"Volume inventory and private API"** — specifically a private gRPC Volume CRUD API for internal consumers. The PRD In Scope only mentions the inventory tracking aspect: *"Every volume is tracked in a central inventory."* It does not mention that a private/internal Volume API exists for CRUD operations by internal consumers (other OSAC services, future public API). This is a meaningful capability gap in the PRD.

**Fix:** Add an In Scope item: *"A private volume management API is available to internal OSAC services for creating, retrieving, listing, and deleting volume records, supporting future integration with tenant-facing volume management."*

---

### Issue 7 — No User Story for Internal/Admin Volume Lifecycle Management via Private API
**Category:** completeness
**Severity:** minor

Related to Issue 6: The private Volume API has an internal consumer (other OSAC services, the future public Volume API covered by OSAC-984). There's no story representing the internal consumer perspective. Since OSAC personas don't include "internal service," this could be noted in an assumption or the story could be written from the CPA or CIA perspective (visibility into full volume lifecycle state), but it's currently absent.

**Fix:** Add a Cloud Provider Admin story: *"As a Cloud Provider Admin, I want volume records to expose the full lifecycle state (creating, available, attached, detached, deleting, deleted) so that I can accurately track and audit storage consumption across the platform."*

---

### Issue 8 — Out of Scope: Vendor REST adapters attribution is misleading
**Category:** scope
**Severity:** minor

The Out of Scope item reads: *"Vendor REST adapters for non-CSI volume management — covered by [OSAC-984]."* The Jira's Out of Scope says this is covered by OSAC-984. However, attributing REST adapters to OSAC-984 (the public Volume API feature) is potentially confusing — REST adapters are a backend implementation concern, not a public API concern. The cross-reference may mislead reviewers into thinking the public API feature owns backend vendor adapters.

**Fix:** Either remove the OSAC-984 reference from the REST adapters item, or clarify: *"Vendor REST adapters for non-CSI volume management — deferred; may be addressed alongside [OSAC-984](https://redhat.atlassian.net/browse/OSAC-984)."*

---

### Issue 9 — Problem Statement Contains Implicit Solution Reference
**Category:** problem-statement
**Severity:** minor

*"OSAC cannot offer block storage as a platform service"* — this is acceptable as a cost-of-inaction statement. However, the phrase *"blocking any tenant workload that requires persistent volumes on CaaS clusters"* slightly anthropomorphizes "OSAC" as the agent. More importantly, the Problem Statement says *"creating a security risk"* without quantifying or qualifying the risk — this is vague. It should be specific about what the risk is (credential exposure, cross-tenant data access, etc.).

**Fix:** Replace *"creating a security risk"* with *"creating a risk of vendor credential exposure and cross-tenant data access."*

---

### Summary Table

| # | Category | Severity | Short Description |
|---|----------|----------|-------------------|
| 1 | design-leakage | important | "Cross-cluster authentication" is implementation language in In Scope |
| 2 | design-leakage | important | "CSI interface" and "per-request" are implementation details in In Scope |
| 3 | design-leakage | important | PVC/StorageClass Kubernetes objects in Tenant User story |
| 4 | completeness | important | CIA missing storage readiness user story |
| 5 | completeness | minor | Missing network reachability and OCP cluster assumptions |
| 6 | completeness | important | Private Volume CRUD API not called out in In Scope |
| 7 | completeness | minor | No user story representing private Volume API consumers |
| 8 | scope | minor | Misleading attribution of REST adapters to OSAC-984 |
| 9 | problem-statement | minor | "Security risk" is vague; specify credential exposure risk |