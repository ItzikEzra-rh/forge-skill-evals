## Design Document Review: OSAC Tenant UI Networking Section

---

### Overall Assessment

The document is well-structured and thorough in many areas. However, it has **critical scope divergences from the PRD** that would cause the wrong product to be built. Several important gaps also exist around PRD-mandated UX patterns and technology choices. Issues are organized by severity.

---

## CRITICAL Issues

### C-1 · Scope · Wrong resource names throughout (ExternalIPs vs. PublicIPs)

The PRD consistently uses **PublicIPs** and **PublicIPPools** and **PublicIPAttachments** (`/api/fulfillment/v1/public_ips`, `/api/fulfillment/v1/public_ip_pools`, `/api/fulfillment/v1/public_ip_attachments`). The design document uses **ExternalIPs**, **ExternalIPAttachments**, and **ExternalIPPools** everywhere, including route paths, API endpoints, component names, workflow descriptions, and test cases.

This is not a naming preference — the PRD specifies the actual API endpoint paths. If the design is implemented as written, developers will call nonexistent endpoints.

**Fix:** Do a complete find-and-replace of ExternalIP → PublicIP, ExternalIPPool → PublicIPPool, ExternalIPAttachment → PublicIPAttachment throughout the entire document. Audit every API call path (e.g., `/api/fulfillment/v1/external_ips` → `/api/fulfillment/v1/public_ips`).

---

### C-2 · Scope · NATGateway is explicitly Out of Scope in the PRD

The PRD Non-Goals state: "NATGateway, ExternalIPAttachment, NetworkClass management (these are provider-only or future scope)." The design document includes NATGateway as a full sub-page with create/delete workflows (Workflow 9), routes (`/networking/nat-gateways`), test cases, and sidebar navigation.

**Fix:** Remove all NATGateway content from the design. This includes Workflow 9, the NATGateway row in the feature table, the `/networking/nat-gateways` routes, NATGateway test scenarios (integration test "NATGateway lifecycle", E2E test "NATGateway lifecycle"), the NATGateway failure mode, NATGateway references in the deletion dependency warning, and the NATGateway state polling section. Update the Non-Goals section to match the PRD's stated reason.

---

### C-3 · Scope · PublicIP Attach/Detach workflows are missing

The PRD requires (FR-27, FR-28): an **Attach** action (side panel with searchable VM list) and a **Detach** action (confirmation modal) as row-level actions on the PublicIPs list page. These are acceptance criteria items. The design document covers only allocation (create) and release (delete) for ExternalIPs/PublicIPs, with no workflow for attaching or detaching a PublicIP from a compute resource.

**Fix:** Add Workflow: Tenant Admin attaches a PublicIP to a VM (opens side panel, selects from eligible ComputeInstances, calls POST `/api/fulfillment/v1/public_ip_attachments`). Add Workflow: Tenant Admin detaches a PublicIP (confirmation modal warning loss of connectivity, calls DELETE on the attachment). Add corresponding failure modes (IP already attached, resource not eligible) and test cases.

---

### C-4 · Scope · VMaaS Wizard Integration is entirely absent

The PRD devotes FR-31 through FR-37 and multiple acceptance criteria to VMaaS Wizard Integration — this is a major deliverable of the feature (inline VN creation from the wizard, smart defaults, blocking VM creation without a network, etc.). The design document has no section, no workflows, no routes, and no test coverage for wizard integration.

**Fix:** Add a dedicated "VMaaS Wizard Integration" section covering: the Network Configuration wizard step, inline Create VN modal overlay (FR-33), smart defaults logic (FR-36), the "no VNs exist" empty state within the wizard (FR-37), Public IP checkbox and IP family selector (FR-34), validation blocking (FR-35), and TanStack Query cache invalidation after inline creation. Add corresponding test scenarios.

---

### C-5 · Scope · NetworkClass exposed in design contradicts PRD

The design includes **Network Class** as a user-visible, required dropdown field in the VirtualNetwork create form (Workflow 2, step 2), populated from `GET /api/fulfillment/v1/network_classes`. The PRD explicitly states: "NetworkClass is assigned automatically by the platform and is not exposed to tenant users" (FR-3, Section 5 Assumptions, Section 6 Dependencies).

**Fix:** Remove the NetworkClass selector from the VirtualNetwork create form and all references to NetworkClass as a user-facing field. Remove `GET /api/fulfillment/v1/network_classes` as a UI-initiated call. Remove the NetworkClass row from the proto→TypeScript mapping table. Update the Non-Goals section to explicitly call out NetworkClass as platform-assigned and not user-facing. The `pnpm gen-types` risk about NetworkClass capabilities can be removed since this field is not user-facing.

---

## IMPORTANT Issues

### I-1 · Consistency · Subnet management model contradicts PRD

The PRD is explicit (FR-13): "Subnets must not have their own top-level sidebar entry — they are managed exclusively from the VirtualNetwork detail page." The design includes `/networking/subnets` as a top-level route and a **Networking → Subnets** sidebar entry. The PRD also specifies subnets are shown on a **tab** of the VirtualNetwork detail page (FR-7, FR-9), not on a standalone list page.

**Fix:** Remove `/networking/subnets` and `/networking/subnets/:id` routes and the Subnets sidebar entry. Redesign Subnet management as the Subnets tab on the VirtualNetwork detail page per FR-7/FR-9. Update the feature table accordingly.

---

### I-2 · Consistency · VirtualNetwork detail page uses wrong pattern (drawer vs. tabbed page)

The PRD requires (FR-6, FR-7): a dedicated VirtualNetwork detail **page** at `/networking/virtual-networks/{id}` with breadcrumb navigation and three **tabs** (Subnets, Security Groups, Details). The design assumes a detail **drawer** (slide-in panel) as the primary pattern for VirtualNetwork, with the full-page route as an alternative being deferred to Open Question 2.

**Fix:** Resolve Open Question 2 now — the PRD mandates a full-page detail view with tabs, not a drawer. Update all references to "detail drawer" for VirtualNetworks to "detail page." Remove the open question or close it with the PRD-specified answer.

---

### I-3 · Consistency · Polling interval contradicts PRD

The design specifies 30-second polling for transitional states (Workflow 10). The PRD specifies 5-second auto-refresh for resources in Provisioning or Deleting state (FR-40, acceptance criteria). The design also describes polling as stopping when "all resources reach terminal states," while the PRD additionally requires disabling Delete actions during transitional states and showing a spinner next to the status badge.

**Fix:** Change the polling interval to 5 seconds. Add the spinner-next-to-status-badge behavior and the disabled Delete action behavior for transitional states, matching FR-40 exactly.

---

### I-4 · Consistency · Button/validation behavior contradicts PRD

The PRD explicitly specifies a distinct validation pattern (FR-4, FR-10, FR-17, FR-21, acceptance criteria): "Create button stays enabled; validation errors highlighted on submit if present" — this is called out as deliberate ("following VM wizard pattern"). The design describes standard client-side validation that prevents submission, which is the opposite pattern.

**Fix:** Update all form descriptions to reflect that the Create button is always enabled, validation errors appear inline after blur or on submit attempt, and invalid submission highlights errors without disabling the submit button.

---

### I-5 · Consistency · Pagination contradicts PRD

The design specifies server-side pagination with `offset`/`limit`, a default page size of 20, and PatternFly `Pagination` components on all list pages. The PRD explicitly rules this out (NFR-9): "Pagination is out of scope for this feature. Existing osac-ui list tables do not use pagination; networking list pages follow the same non-paginated pattern."

**Fix:** Remove all pagination implementation details, the PatternFly Pagination component references, the `offset`/`limit` query parameters, and the default-page-size-20 specification. Note in the Implementation Details that pagination is deferred per PRD NFR-9.

---

### I-6 · Consistency · Technology stack mismatch (data fetching)

The PRD mandates (NFR-2): **TanStack Query (React Query)** for data fetching and **Connect-ES for gRPC-Web client integration**. The design uses an "authenticated-fetch pattern" and generated TypeScript client from `pnpm gen-types` with no mention of TanStack Query hooks or Connect-ES. The PRD also specifies (FR-43, NFR-3) that TanStack Query hooks (`useVirtualNetworks`, `useCreateVirtualNetwork`, etc.) must be created in `libs/ui-components/src/api/v1/`.

**Fix:** Replace all references to "authenticated-fetch pattern" and the generic "API client" with TanStack Query hooks and Connect-ES. Add a section specifying the hooks to be created per the pattern named in FR-43. Remove the pnpm gen-types assumption as the primary type-generation mechanism; use `libs/types/src/osac/public/v1/` (protobuf-generated, per FR-43/NFR-3).

---

### I-7 · Completeness · VirtualNetwork detail page tabs not described

The PRD requires three tabs on the VirtualNetwork detail page (FR-7): Subnets (default), Security Groups, Details. The design describes a detail drawer with spec and status fields but does not specify the tab structure, what each tab contains, or the Subnets-as-tab pattern. This is the primary entry point for Subnet management per the PRD.

**Fix:** Add a detailed description of the VirtualNetwork detail page: breadcrumb navigation, page title (VN name), status badge, key properties (CIDRs), Delete action in header, and the three-tab structure with content for each tab.

---

### I-8 · Completeness · SecurityGroup accessible from VN detail page (not just sidebar)

The PRD requires (FR-21): SecurityGroups must be accessible from both the sidebar AND the VirtualNetwork detail page's Security Groups tab. The design only describes the standalone SecurityGroups list page and its own create flow; there is no description of how SecurityGroups appear in or are created from the VN detail page's Security Groups tab.

**Fix:** Add description of the Security Groups tab on the VirtualNetwork detail page, including the pre-selected VN context when "Create Security Group" is triggered from that tab (FR-17).

---

### I-9 · Completeness · Empty state specifications missing

The PRD requires (FR-38, acceptance criteria): all list pages must show empty states with illustrations, helpful headings (e.g., "No virtual networks yet"), descriptions, and primary action buttons. The design does not describe empty state components anywhere.

**Fix:** Add an empty state specification for each list page, specifying the illustration, heading text, description text, and CTA button label.

---

### I-10 · Completeness · Subnet deletion guard is wrong

The PRD (FR-14): deletion of a Subnet is blocked if it has attached compute instances. The design (Workflow 4) only mentions the VirtualNetwork deletion guard (Subnets, SecurityGroups as children of VN). There is no Subnet-level deletion guard described.

**Fix:** Add a Subnet delete workflow with the pre-condition check: if the subnet has attached compute instances, block deletion and show the error directing the user to remove or migrate instances first.

---

### I-11 · Completeness · SecurityGroup deletion guard is wrong

The PRD (FR-22): deletion of a SecurityGroup is blocked if it is attached to compute instances. The design does not describe this guard for SecurityGroups.

**Fix:** Add the SecurityGroup deletion guard to the SecurityGroup delete workflow and failure modes.

---

### I-12 · Completeness · PublicIP deletion guard missing

The PRD (acceptance criteria, FR-28): deletion of a PublicIP is blocked if it is currently attached. The design does not describe this guard.

**Fix:** Add the PublicIP delete workflow including the attached-IP blocking behavior and appropriate error message.

---

### I-13 · Depth · VirtualNetwork list page columns do not match PRD

The design specifies VirtualNetwork list columns as: Name, IPv4 CIDR, IPv6 CIDR, Network Class, State, Created (Workflow 1, step 4). The PRD specifies (FR-1): Name, IPv4 CIDR, **Subnets count**, and Status. The design adds IPv6 CIDR, Network Class, and Created; omits Subnets count.

**Fix:** Update the VirtualNetwork list page column specification to: Name, IPv4 CIDR, Subnets count, Status. Remove IPv6 CIDR, Network Class, and Created from the primary column list (they belong in the detail view).

---

### I-14 · Depth · Retry behavior for failed resources not specified

The PRD (FR-41): for failed resources, the UI must show the error in a collapsible alert on the detail page and provide Retry and Delete actions. Retry re-submits the original POST. The design addresses the FAILED state badge and message display but does not describe the Retry action or the collapsible alert pattern.

**Fix:** Add a failed-resource section specifying the collapsible alert, Retry button behavior (re-POST), and Delete action for resources in FAILED state.

---

### I-15 · Depth · Optimistic updates not specified

The PRD (FR-42): the UI must show optimistic updates for delete operations (gray out the row immediately). The design does not mention optimistic updates.

**Fix:** Add optimistic delete behavior: gray out the row immediately on delete confirmation, using TanStack Query's optimistic update pattern.

---

### I-16 · Depth · Auto-refetch on window focus not specified

The PRD (FR-42): the UI must auto-refetch on window focus (TanStack Query's `refetchOnWindowFocus`). The design does not mention this.

**Fix:** Add a note in the API client/data-fetching section specifying `refetchOnWindowFocus: true` and the Refresh button in the toolbar per FR-42.

---

### I-17 · Consistency · VirtualNetwork create form: IPv4 CIDR is required, range-constrained

The PRD (FR-3): IPv4 CIDR is **required** (not optional) with a **/16 to /24 range** constraint. The design (Workflow 2) makes IPv4 CIDR optional ("optional unless IPv6 also absent") with no range constraint, and adds IPv6 CIDR as always visible.

**Fix:** Mark IPv4 CIDR as required in the create form. Add the /16 to /24 range validation. IPv6 CIDR remains optional. Align the validation rules in the test plan to match.

---

### I-18 · Consistency · SecurityGroup rule fields differ from PRD

The PRD (FR-18, FR-20) specifies SecurityGroup rules have: Protocol, Port Range (single text input, not Port From/Port To), and Source/Destination CIDR. FR-20 also adds Description as a column. The design specifies separate Port From / Port To inputs and omits Description.

**Fix:** Align the rule editor fields with the PRD: Protocol dropdown, Port Range text input (single field), Source/Destination CIDR, Description. Update unit tests for the rule editor accordingly.

---

## MINOR Issues

### M-1 · Structure · `authors` field is TBD

The YAML frontmatter has `authors: TBD`. This is the final document; author(s) should be filled in.

**Fix:** Populate with actual author names before submission.

---

### M-2 · Structure · "UX Alignment" section heading is non-standard

The section titled "UX Alignment" contains what is effectively a proto-to-TypeScript field mapping table. The OSAC EP template uses "Implementation Details/Notes/Constraints" as the implementation catch-all. The proto mapping is useful content but is buried under a misleading heading.

**Fix:** Move the proto→TypeScript mapping table into Implementation Details. Rename or remove the "UX Alignment" section, or repurpose it to describe actual UX design decisions (drawer vs. page, empty state patterns, etc.).

---

### M-3 · Completeness · Open Question 4 (ExternalIPPool CEL filter) references wrong resource name

Open Question 4 asks about `status.available > 0` filter for ExternalIPPool. This should reference PublicIPPool