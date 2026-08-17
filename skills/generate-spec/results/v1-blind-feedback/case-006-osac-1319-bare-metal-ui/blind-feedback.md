## Review: OSAC-1319 Bare Metal Instance UI

Overall assessment: This is a well-structured, thorough design document. The implementer coverage is strong, failure handling is concrete, and the PRD alignment is tight. The issues below are real problems worth fixing, not nitpicks.

---

### CRITICAL

**[scope / consistency] Start/Stop disabled-state logic contradicts itself across two sections**

The action semantics table (Instance Management section) says Start is disabled when `PROVISIONING, DELETING, or FAILED`. The `BareMetalActionButtons` implementation section repeats the same rule. But the `BareMetalStatusLabel` table lists a `HALTED` state as a valid display state, yet the action table never mentions `HALTED` as a state in which Start should be *enabled* — it only lists the conditions under which it's disabled. The table also conflates `run_strategy` with `state`: Start is described as disabled when state is PROVISIONING/DELETING/FAILED, but the trigger condition (`run_strategy: HALTED → Start`) uses `run_strategy`, not state. It's not established whether an instance can be in `RUNNING` state with `run_strategy: HALTED`, or HALTED state (a state that doesn't appear in the state machine at all — the status label table lists PROVISIONING/RUNNING/FAILED/DELETING but not HALTED). The document needs to reconcile the state machine (what states the API returns in `status.state`) versus the power-mode field (`spec/status.run_strategy`) and define which field drives button visibility versus disabled state. Right now a developer implementing `BareMetalActionButtons` would have to guess.

**Fix:** Add a state-machine diagram or table that explicitly enumerates every `BareMetalInstanceState` enum value, maps `run_strategy` values to those states, and specifies for each combination whether Start, Stop, Restart, and Delete are shown/hidden/enabled/disabled.

---

**[depth] `BareMetalNoNetworkingStep` assumption is load-bearing but unresolved**

The document acknowledges in both the Proposal and Risks sections that `CatalogProvisionWizard` requires a `NetworkingStep` slot, and that a no-op component will be passed. But the assumption is bracketed `[Assumption: NetworkingStep slot accepts a null-rendering component]` — meaning it's unknown whether the interface accepts this. If it doesn't (e.g., if `CatalogProvisionWizard` always renders a "Networking" nav step label regardless of what's passed), the wizard will show a blank step to users, which is a UX defect. This is Open Question territory but it isn't listed as an open question.

**Fix:** Either resolve this before merging (check `CatalogProvisionWizard`'s source and remove the assumption bracket), or promote it to Open Question #4 with a fallback — e.g., "if the slot is not skippable, use a bespoke two-step form for bare metal instead."

---

### IMPORTANT

**[consistency] Route collision: `/bare-metal/create/:catalogItemId?` vs `/bare-metal/:id`**

`BareMetalRoutes.tsx` defines:
- `/bare-metal/create/:catalogItemId?` → `BareMetalCreatePage`
- `/bare-metal/:id` → `BareMetalDetailsPage`

If the router evaluates routes in declaration order and `:id` is a wildcard segment, navigating to `/bare-metal/create` (no catalog item ID) could match `/bare-metal/:id` with `id = "create"` depending on which route is declared first. The document doesn't specify route ordering or whether a guard (e.g., `id !== 'create'`) is needed on the detail route.

**Fix:** Specify that `/bare-metal/create` is declared before `/bare-metal/:id`, or use a more discriminating pattern such as `/bare-metal/new/:catalogItemId?` for the create route to avoid the ambiguity entirely.

---

**[depth] `image.sourceType` hardcoding is undocumented at the API level**

The document states `sourceType` is hardcoded to `"registry"` in `buildCreatePayload`. But it's never established what values `image.sourceType` accepts per the OSAC-1118 API, whether `"registry"` is the only valid value, or whether the fulfillment-service would reject a different value. If `"registry"` is the only valid value, the field shouldn't appear in the payload schema at all and the wire format should be documented. If other values exist, they're silently unsupported — which should be noted as a known limitation.

**Fix:** Add a note in the UX Alignment table row for `spec.image.sourceRef` citing the OSAC-1118 EP's enumeration of `sourceType` values, and state explicitly whether `"registry"` is the only valid value or whether others are intentionally deferred.

---

**[scope] PRD requires inline row actions on the list page; design partially satisfies this but omits column detail**

The PRD explicitly requires "Instance lifecycle actions (power toggle, restart, delete) available directly on the instance list page (inline row actions)." The design acknowledges this with `[PRD: In Scope — inline row actions]` on the list table column description. However, the `BareMetalActionButtons` implementation section says the component is "rendered in two contexts: as Actions column in each list row and as the action toolbar on the detail page" — but then the entire implementation detail focuses on the detail-page context. The list-row context gets no treatment: how are actions laid out in a narrow table cell? Does the power toggle show as Start or Stop depending on per-row state? Is there a truncated kebab menu fallback for narrow viewports? PatternFly table rows with four action buttons in a cell are non-trivial.

**Fix:** Add a subsection or note under `BareMetalListPage` describing the list-row action layout: whether all four buttons are inline, whether a kebab overflow is used, and how the same `BareMetalActionButtons` component adapts its rendering between list and detail contexts (prop or variant).

---

**[completeness] No treatment of pagination or large result sets on the list page**

`BareMetalListPage` is described with columns and an empty state but no pagination strategy. The existing `VmListPage` presumably has one. If the fulfillment-service returns unbounded lists, a tenant with hundreds of instances gets an unusable page. If server-side pagination exists, the design should note the page size and how `useBareMetalInstances` handles cursor/offset parameters. If client-side filtering is used, say so.

**Fix:** Add one sentence to the list page description stating whether the page uses server-side pagination (and the default page size), client-side slicing, or infinite scroll — and whether the existing `useBareMetalInstances` hook already supports a `pageToken` or `limit` parameter.

---

**[depth] Polling interval not specified**

The document references "TanStack Query refetch interval" in three places but never states what the interval is. For a provisioning operation that may take minutes, the polling rate is a user-experience decision (too slow = stale UI; too fast = unnecessary load). The VM adapter's interval should be cited as the baseline, and the bare metal interval should be either matched or justified.

**Fix:** State the polling interval explicitly (e.g., "10-second refetch interval, matching `useComputeInstance`") in the TanStack Query references, or note it as a decision deferred to implementation with a recommended default.

---

**[consistency] Open Question #1 is answered inline but still listed as open**

Open Question #1 asks whether `PATCH` supports partial updates. The Implementation Details section answers it: "The PATCH hook sends only the mutated field... consistent with the existing `usePatchComputeInstance` pattern." If the pattern is established and already works for VMs, this isn't an open question — it's a confirmed design decision. Leaving it open implies uncertainty that doesn't exist.

**Fix:** Remove Open Question #1 or rephrase it as a confirmed assumption: "Confirmed: fulfillment-service PATCH endpoint supports partial updates, following the `PATCH /compute_instances/{id}` pattern."

---

**[depth] Wizard field_definitions overlay behavior needs a concrete example for the BM case**

The document describes `field_definitions` overlaying fields in the Configuration step, but doesn't give a concrete example for the bare metal case. The VM adapter reference is cited, but bare metal has a different field set (user data, image source) and it's not clear which of these fields a catalog item's `field_definitions` could lock down. For an implementer who hasn't read the VM adapter source, this is too abstract.

**Fix:** Add one concrete example: e.g., "A catalog item with `field_definitions: [{path: 'spec.userData', editable: false, default: '#!/bin/bash\ninstall-agent.sh'}]` would render user data as a read-only field pre-filled with the default value." This makes the overlay semantics unambiguous.

---

### MINOR

**[structure] "UX Alignment" section title is non-standard**

OSAC EPs use "Implementation Details/Notes/Constraints" for technical mapping content. The "UX Alignment" section appears between Proposal and Implementation Details and duplicates context that would naturally live inside the Implementation Details adapter subsection. The section header is also misleading — it contains a field mapping table (a technical artifact), not UX guidance.

**Fix:** Fold the field mapping table into the `useBareMetalInstanceAdapter` subsection under Implementation Details, or rename it to "API Field Mapping" for clarity.

---

**[completeness] No mention of i18n / translation for new user-visible strings**

The design introduces approximately 15–20 new user-visible strings (button labels, column headers, error messages, state labels, empty-state copy). OSAC conventions require all UI strings to go through the `t()` translation function. The nav entry shows `t('Bare Metal')` correctly, but the remaining strings (e.g., "Provision bare metal", "Create bare metal instance", "Bare Metal Machines", error messages) are written as plain string literals throughout the document.

**Fix:** Add a note in Implementation Details that all user-visible strings use `t()`, and flag the error-message strings specifically — since server error messages are passed through to the user, note whether they are translated or shown verbatim.

---

**[completeness] Accessibility not addressed until GA graduation criteria**

The design defers accessibility review to GA. PatternFly components are accessible by default, but custom components (`BareMetalStatusLabel` with color tokens, `BareMetalConditionsList`, the action button disabled states) require `aria-label`, `aria-disabled`, and color-contrast attention at authoring time, not retroactively.

**Fix:** Add one sentence in Implementation Details noting that PatternFly color tokens satisfy WCAG AA contrast requirements for status labels, and that disabled buttons include `aria-disabled="true"` and tooltip text explaining why the action is unavailable — consistent with the VM page implementation.

---

**[tests] E2E test for "Empty catalog" doesn't specify how the empty state is induced**

The E2E test "Empty catalog: with no published BareMetalInstanceCatalogItem, the catalog section shows an appropriate empty state" doesn't say how the test arranges the precondition — whether the test environment starts with no catalog items, whether items are deleted/unpublished as part of setup, or whether the mock API returns an empty list. Without this, the test is unimplementable without guessing.

**Fix:** Specify the setup step: e.g., "Test environment is seeded with zero published `BareMetalInstanceCatalogItem` records; the bare metal filter is applied on the Catalog page."

---

**[depth] `BareMetalDeleteConfirmModal` confirmation content not specified**

The design names the component and says it opens on delete click, but doesn't specify what the confirmation dialog says. For destructive actions, the dialog copy matters — it should tell the user what will be deleted (instance name) and that the action is irreversible. The `VmDeleteConfirmModal` is cited as the mirror, but without seeing that component's copy, an implementer could write anything.

**Fix:** Add one line specifying the confirmation dialog pattern: e.g., "Dialog displays instance name and the text 'This action cannot be undone. The instance and all associated data will be permanently deleted.' Confirm button labeled 'Delete', cancel button labeled 'Cancel' — matching `VmDeleteConfirmModal` copy with substituted resource type."