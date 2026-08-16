# Judge Feedback -- Issues to Fix

## Implementation Depth (PARTIAL, scored 1/2)

The generated document has substantial implementation detail (specific error codes like ALREADY_EXISTS/FAILED_PRECONDITION/ABORTED, validation rules with regex patterns, API endpoints, state transitions, polling logic) but lacks the gold standard's specificity in several areas: missing TanStack Query refetchInterval code examples, missing Formik/Yup schema details, missing exact TypeScript mutation hook implementations, and missing the concrete file structure with current vs. new code distinctions.

Evidence:
- export const useCreateVirtualNetwork = () => {
- refetchInterval: (data) => { const hasNonTerminalState
- spec.ipv4_cidr`: required, valid CIDR notation, prefix length between /16 and /24 (Yup regex

## Workflow Completeness (FAIL, scored 1/2)

The generated document covers create/read/update/delete lifecycle and error paths thoroughly, but uses 'Tenant Admin' and 'Tenant User' only (missing Cloud Provider Admin and Cloud Infrastructure Admin personas), and the Mermaid diagram covers only VirtualNetwork creation rather than the multi-step VMaaS wizard provisioning flow shown in the gold standard.

Evidence:
- #### Actor definitions
- - **Tenant Admin** — a user with the `tenant-admin` Keycloak role
- - **Tenant User** — a user with the `tenant-user` Keycloak role

## Failure Handling (PARTIAL, scored 1/2)

The generated document covers most concrete failure modes but misses controller reconciliation failures as a distinct category (only mentions resources stuck in PENDING), and lacks the specific retry/exponential-backoff behavior for GET requests and the idempotency/double-submission prevention detail found in the gold standard.

Evidence:
- ExternalIP stuck in PENDING | `ExternalIP` status.message in detail view + osac-operator controller logs | AAP job failure
- Optimistic locking conflict (ABORTED)
- fulfillment-service unavailable

## Content Completeness (PARTIAL, scored 1/2)

The generated document covers the same overall scope (networking UI, list/detail/CRUD pages, wizard integration, no backend changes) but has substantive content gaps: it describes different resource types (ExternalIPs/ExternalIPAttachments/NATGateways instead of PublicIPs/PublicIPAttachments), omits the concrete TanStack Query implementation details and file structure from gold standard, misses the VMaaS wizard inline creation focus as a key architectural pattern, and lacks the specific existing code hooks (useVirtualNetworks, VmNetworkingStep.tsx) and their extension patterns that are central to the gold standard.

Evidence:
- three categories of UI components
- VmNetworkingStep.tsx: inline VirtualNetwork creation modal
- useCreateVirtualNetwork, useDeleteVirtualNetwork

## Scope Discipline (PARTIAL, scored 1/2)

The generated document largely matches PRD scope but has notable deviations: it covers ExternalIPs/ExternalIPAttachments/NATGateways as top-level sections while the gold standard explicitly puts these as non-goals (provider-only) and uses 'PublicIPs' terminology; the gold standard's Non-Goals explicitly exclude NATGateway and ExternalIPAttachment UI which the generated doc includes.

Evidence:
- Non-Goals: Provider-only resource management (NetworkClass CRUD, PublicIPPool CRUD, NATGateway, ExternalIPAttachment)
- ExternalIPAttachments | List, Get, Create, Delete
- NATGateways | List, Get, Create, Delete

