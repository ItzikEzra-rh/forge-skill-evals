## Design Document Review: caas-cluster-storage

---

### Overall Assessment

This is a well-structured, substantive design document. It covers the PRD scope faithfully, provides implementer-level detail, and follows OSAC conventions. The issues below are real but mostly important-to-minor. There are no critical scope violations.

---

## Issues Found

---

### 1. SCOPE — Important

**Section:** Non-Goals

**What's wrong:** The Non-Goal "Dynamic tier addition to running CaaS clusters (beyond v0.1)" is stated without any corresponding PRD basis. The PRD says nothing about tier addition being out of scope — it only calls out StorageTier API integration (OSAC-1110). This is a design-originated scope exclusion presented without justification, and it may silently conflict with Tenant User Story 2 ("select a storage tier via StorageClasses"). If tiers are fixed at cluster creation time, that story is only partially satisfied and the document should say so explicitly.

**Fix:** Either cite a PRD basis or move this to Drawbacks/Open Questions with an explicit note that the PRD does not exclude this and it's a v0.1 deferral decision made by the design author.

---

### 2. DEPTH — Important

**Section:** Kubeconfig Retrieval / Security Considerations

**What's wrong:** The document states the kubeconfig "is not persisted anywhere outside the AAP job payload" and that AAP tasks use `no_log: true`. However, it never addresses what happens to the kubeconfig inside the AAP job payload itself — specifically whether the job's extra-vars are encrypted at rest in AAP, whether they appear in AAP's job history UI, and what the retention policy is. This is a meaningful security gap for a credential passing across a trust boundary.

**Fix:** Add a sentence in Security Considerations covering AAP job extra-vars storage: whether AAP encrypts extra-vars at rest, whether `SENSITIVE_VARIABLES` is set for `admin_kubeconfig` in the job template, and what log scrubbing applies in AAP itself (not just the playbook tasks).

---

### 3. DEPTH — Important

**Section:** Reconciliation Flow / `handleUpdate`

**What's wrong:** Step 3 says "Trigger or poll the AAP job tracked in `ClusterOrder.Status.ClusterStorageJobs`" but the document never specifies the trigger condition for moving from "trigger" to "poll." Specifically: how does the controller distinguish a `ClusterOrder` that has never had a job launched from one that has a job in-flight? The document mentions `ClusterStorageJobs` reuse is an open question (Open Question 3), but then uses the field as if its semantics are settled throughout the reconciliation flow and the test plan. This is an internal inconsistency.

**Fix:** Either resolve Open Question 3 inline (define: "if `ClusterStorageJobs` contains a job with matching trigger conditions and status `Running`, poll; if empty or all jobs terminal, launch new") or mark the reconciliation flow step explicitly as "TBD pending answer to Open Question 3." Do not leave settled-looking pseudocode depending on an unresolved question.

---

### 4. CONSISTENCY — Important

**Section:** Failure Handling — "AAP provisioning job fails" row / Reconciliation Flow

**What's wrong:** The failure table says "Retries when the `ClusterOrder` or a related resource (Tenant, HostedControlPlane) changes." The reconciliation flow says the controller does not add a retry timer. But if the AAP job fails and no resource changes (e.g., the Tenant and HostedControlPlane are stable), the `ClusterOrder` will stay in `ClusterStorageReady=False` indefinitely with no automatic retry. This is correct behavior but it contradicts the failure table's implication that retry is automatic.

**Fix:** Clarify in the failure table: "Retries on resource change event only — no polling timer. If no resource changes, a Cloud Provider Admin must trigger a reconcile (e.g., annotate the `ClusterOrder`)." Add a Support Procedures entry for manually triggering reconciliation.

---

### 5. DEPTH — Important

**Section:** RBAC — Secrets access

**What's wrong:** The document says the controller needs `get` on `secrets` "in HostedCluster namespaces" and references the existing `hub-access-hosted-clusters` ClusterRole. However, `ClusterRole` grants are cluster-scoped; to limit Secret access to specific namespaces you need per-namespace `Role`/`RoleBinding`, not a `ClusterRole`. The document says "Add the storage controller's ServiceAccount to the per-namespace RoleBinding," which implies namespace-scoped binding, but then also says "All additions are to the existing `osac-operator-controller-manager` ClusterRole." These two statements contradict each other.

**Fix:** Be explicit: the Secret `get` is granted via per-namespace `RoleBinding` (not `ClusterRole`), and the `hostedcontrolplanes` `get` is granted via `ClusterRole`. Show the two distinct grant paths separately.

---

### 6. PROTO / API — Minor

**Section:** API Extensions — ClusterOrder CRD

**What's wrong:** The document defines the new `ClusterOrderConditionClusterStorageReady` constant and the four condition reasons in a table, but does not show the Go struct additions for the reasons as typed constants. The existing OSAC convention (visible in the `ClusterOrderConditionType` pattern shown) uses typed reason constants. Untyped string reasons drift over time.

**Fix:** Add a Go snippet defining reason constants:

```go
const (
    ReasonKubeConfigNotAvailable = "KubeConfigNotAvailable"
    ReasonProvisionFailed        = "ProvisionFailed"
    ReasonMultipleFound          = "MultipleFound"
    ReasonClusterStorageProvisioned = "ClusterStorageProvisioned"
)
```

---

### 7. WORKFLOWS — Minor

**Section:** Workflow Description — CaaS Storage Provisioning

**What's wrong:** The sequence diagram shows `SC->>SC: Poll ClusterStorageJobs until Succeeded` as a single step, but the reconciliation is event-driven (no polling timer). In practice the controller sets a watch and re-enters the reconcile loop on job status changes. The diagram implies a blocking poll loop inside a single reconciliation, which is architecturally incorrect and will confuse implementers.

**Fix:** Revise the diagram to show the controller returning after triggering the AAP job, and re-entering on a subsequent reconcile event when the job status changes. Add a note on the diagram: "Controller returns; AAP job completion triggers next reconcile."

---

### 8. TESTS — Minor

**Section:** Test Plan — Integration Tests

**What's wrong:** The integration test "Simulate AAP job failure (mock returns error)" does not specify what the mock returns — an HTTP error, a job object with `status: failed`, or a timeout. The distinction matters because the controller behavior differs (immediate `ProvisionFailed` vs. timeout-based retry). The other integration tests are adequately specified.

**Fix:** Specify: "Mock AAP returns job object with `status.phase=Failed` and a non-empty `failureMessage`." Separate from a connection-error scenario if that case is also exercised.

---

### 9. COMPLETENESS — Minor

**Section:** Upgrade / Downgrade Strategy

**What's wrong:** The upgrade path states that existing `ClusterOrder` objects with `Phase=Ready` will be picked up on first reconciliation and storage provisioning triggered automatically. This is correct, but the document does not address what happens to clusters that have `Phase=Ready` and storage was already manually configured (e.g., a Cloud Provider Admin manually installed the CSI driver before this feature shipped). The controller will trigger a re-provisioning AAP job against an already-configured cluster.

**Fix:** Add a note: "If storage was manually pre-configured on existing clusters, the AAP role must be idempotent (no destructive re-creation). Confirm with the `osac-aap` team that `ensure_storage_class.yaml` is idempotent (i.e., creates StorageClasses only if absent). If not, Cloud Provider Admins must pre-set `ClusterStorageReady=True` on affected `ClusterOrder` objects before upgrade to suppress re-provisioning."

---

### 10. COMPLETENESS — Minor

**Section:** Open Questions

**What's wrong:** There is no open question about the `ClusterOrder` finalizer interaction with the HyperShift cluster deletion sequence. Specifically: when a HostedCluster is deleted, does the HostedControlPlane go away before or after the ClusterOrder? If the ClusterOrder is deleted by the HyperShift controller before OSAC's finalizer teardown completes, that's a race. The failure table covers the HostedControlPlane-gone case but doesn't address ordering guarantees.

**Fix:** Add Open Question 4: "What is the deletion order between `ClusterOrder` and `HostedControlPlane` when a HostedCluster is deleted? Does HyperShift delete the HostedControlPlane before or after the ClusterOrder is removed? This determines whether the HostedControlPlane-gone teardown path is a rare edge case or the common path."

---

## Summary Table

| # | Category | Severity | Section |
|---|---|---|---|
| 1 | Scope | Important | Non-Goals — tier addition deferral not PRD-backed |
| 2 | Depth | Important | Security — AAP extra-vars encryption/retention not addressed |
| 3 | Depth / Consistency | Important | Reconciliation — Open Q3 contradicts settled-looking flow |
| 4 | Consistency | Important | Failure table — retry claim contradicts event-driven-only model |
| 5 | Depth | Important | RBAC — ClusterRole vs. per-namespace RoleBinding contradiction |
| 6 | Structure / API | Minor | API Extensions — reason constants not typed |
| 7 | Workflows | Minor | Sequence diagram — blocking poll implied, should show re-entry |
| 8 | Tests | Minor | Integration — AAP failure mock underspecified |
| 9 | Completeness | Minor | Upgrade — pre-configured clusters not addressed |
| 10 | Completeness | Minor | Open Questions — HyperShift deletion ordering gap |