## PRD Review: OSAC-1319 BareMetal Instance UI

---

### Issue 1 — Design Leakage in User Stories

**Category:** design-leakage
**Severity:** important

**What's wrong:** Several user stories expose internal API field names and implementation details that belong in a design/engineering spec, not a PRD:

- "toggle the run strategy between always-on and halted" — *run strategy* is an API field name leaking into requirements
- "restart a running instance from the detail view so that I can recover from issues without reprovisioning" — acceptable, but "restart_requested_at" is referenced indirectly via the Jira's PATCH mechanic; this doesn't appear in the PRD directly, so this one is fine
- The user story for run strategy toggle and the spec summary story references "run strategy, SSH key present/absent, user data present/absent" — these are API field names

**What to fix:** Reframe in outcome language. Instead of "toggle the run strategy between always-on and halted," write "change the power state of an instance between always-on and halted." "Run strategy" is an implementation-level concept; the PRD should describe what the user *achieves*, not the API knob they turn.

---

### Issue 2 — Design Leakage in User Stories (API endpoints)

**Category:** design-leakage
**Severity:** minor

**What's wrong:** The Jira description mentions specific API endpoints (`GET /api/fulfillment/v1/baremetal_instance_catalog_items`, `POST /api/fulfillment/v1/baremetal_instances`, `PATCH run_strategy`, `PATCH restart_requested_at`). None of these appear in the PRD user stories, which is **correct**. However, the Out of Scope section says "UI screens that consume existing API endpoints" — this is acceptable platform vocabulary, not a specific endpoint reference. No fix needed here.

---

### Issue 3 — Problem Statement Contains Mild Solution Language

**Category:** problem-statement
**Severity:** important

**What's wrong:** The final sentence of the Problem Statement reads: *"creates an inconsistent experience compared to ComputeInstance, which already has full UI coverage."* While framing inconsistency as a problem is valid, the phrase "full UI coverage" implicitly describes the solution (UI coverage is what is being built) and anchors the problem statement to the proposed fix rather than the user pain.

**What to fix:** Rewrite to focus purely on the pain: "creates an inconsistent experience that forces some workloads to require different tooling than others, fragmenting operator workflows." Remove the reference to ComputeInstance's UI coverage state.

---

### Issue 4 — Markdown Rendering Missing from Scope / User Stories

**Category:** completeness
**Severity:** important

**What's wrong:** The Jira explicitly specifies: *"description (Markdown-rendered)"* for the catalog item browser. Neither the In Scope section nor any user story mentions Markdown rendering of descriptions. The PRD user story only says "showing title, description, and hardware summary" — it drops the rendering requirement entirely.

**What to fix:** Add to the catalog browsing user story that descriptions are rendered as formatted text (not raw markup), or add it as an explicit In Scope bullet. This is a distinct capability from just displaying a description string.

---

### Issue 5 — Catalog Item Linked in Instance List Missing from User Stories

**Category:** completeness
**Severity:** minor

**What's wrong:** The Jira specifies the catalog item column in the instance list is **linked** (i.e., navigates to the catalog item detail). The PRD In Scope mentions "instance list" and the user story says "showing name, catalog item, state, and age" but does not capture that the catalog item is a navigable link to the catalog entry. This is a distinct UX behavior, not just a display concern.

**What to fix:** Update the instance list user story to specify that the catalog item shown is a link that navigates to the catalog item detail view.

---

### Issue 6 — Power Toggle Disabled States Not Captured

**Category:** completeness
**Severity:** important

**What's wrong:** The Jira specifies that the power toggle is "disabled while PROVISIONING or DELETING" and the Restart button is "disabled unless state is RUNNING" and Delete is "disabled while DELETING." The PRD user story for the run strategy toggle and restart makes no mention of these disabled/enabled state conditions. These are meaningful behavioral requirements that affect what a tenant can do, not implementation details.

**What to fix:** Add to the relevant user stories (or a dedicated story) that lifecycle actions are conditionally available based on instance state. For example: "I want lifecycle actions (power toggle, restart, delete) to be unavailable when the instance is in a transitional state (provisioning or deleting) so that I cannot trigger conflicting operations." This is user-visible behavior, not design leakage.

---

### Issue 7 — Async Status Coverage Is Partial

**Category:** completeness / async-status
**Severity:** minor

**What's wrong:** The PRD does address provisioning state visibility ("surface provisioning state and error details") in the In Scope section and in the instance detail user story. However, there is no user story or scope item addressing what the tenant sees *during* the create flow after submitting — i.e., is the tenant redirected to the list, to the detail view, or shown a pending state inline? Given that BareMetalInstance provisioning is asynchronous and can take meaningful time, the post-submit experience is a gap.

**What to fix:** Add a user story or clarify in scope: "After submitting a create request, I want to be taken to the instance detail view showing the current provisioning state so that I can track progress without navigating manually."

---

### Issue 8 — `field_definitions` Hardware Profile Summary Not Addressed

**Category:** completeness
**Severity:** minor

**What's wrong:** The Jira says the hardware profile summary in the catalog browser comes "from field_definitions." While the PRD correctly avoids the field name (good — avoiding design leakage), it also doesn't clarify what "hardware summary" means to the user. "Hardware summary" is vague; the Jira implies it's structured data from the profile definition (CPU, RAM, disk, etc.).

**What to fix:** In the catalog browsing user story, replace "hardware summary" with a user-outcome description such as "key hardware specifications (such as CPU, memory, and storage)" so the requirement is unambiguous without leaking the internal field name.

---

### Summary

| # | Category | Severity | Short Description |
|---|----------|----------|-------------------|
| 1 | design-leakage | important | "Run strategy" API field name used in user stories |
| 3 | problem-statement | important | Solution language in Problem Statement |
| 4 | completeness | important | Markdown rendering of descriptions not captured |
| 5 | completeness | minor | Catalog item link in instance list not captured |
| 6 | completeness | important | Action disabled-states missing from user stories |
| 7 | completeness/async | minor | Post-submit redirect/state not addressed |
| 8 | completeness | minor | "Hardware summary" too vague without field_definitions context |

**Overall:** The PRD is well-structured and covers the major flows. The most important fixes are capturing the action disabled-states (Issue 6), Markdown rendering (Issue 4), and cleaning up problem statement solution language (Issue 3). Template compliance and persona coverage are correct.