# BareMetal Instance UI

| Field       | Value   |
|-------------|---------|
| Author(s)   | Adrien Gentil |
| Jira        | [OSAC-1319](https://issues.redhat.com/browse/OSAC-1319) |
| Date        | 2026-08-12 |

## Problem Statement

Tenants currently have no web console interface to discover bare metal catalog offerings, provision bare metal instances, or manage their lifecycle. All bare metal operations require direct API or CLI interaction, which raises the barrier to entry for tenants who prefer click-ops workflows and creates an inconsistency with the existing ComputeInstance UI experience. Without a tenant-facing UI, bare metal adoption is limited to API-savvy users, and tenants cannot visually browse catalog items, monitor instance state, or perform power and lifecycle actions through the console.

## In Scope

- Tenant-facing UI screens for the full BareMetalInstance lifecycle: catalog browsing, instance listing, creation, detail view, and day-2 actions (start, stop, restart, delete).
- Read-only catalog item browser for discovering available bare metal offerings (title and description) before provisioning.
- Instance state visibility including status badges and error details when an instance is in a failed state.
- Client-side validation for SSH public key format (OpenSSH) and user data size (max 64 KB).
- Visual consistency with the existing ComputeInstance list layout.

## Out of Scope

- Cloud Provider Admin catalog item management (create/edit/delete of catalog items) — admin-only via private API, not part of tenant UI.
- BareMetalInstance API or backend changes — this feature covers the UI layer only.
- Exposing or selecting run strategy in the creation wizard, detail view, or list view — power state is controlled exclusively through start and stop actions.
- OS image selection — this field is currently under active API development and may become mandatory in a future iteration; it is excluded from the initial UI scope.

## User Stories

### Tenant User

- As a Tenant User, I want to browse a catalog of bare metal offerings showing title and description so that I can choose the right catalog item before provisioning.
- As a Tenant User, I want to see a list of my bare metal instances showing name, catalog item, state, and age so that I can monitor my fleet at a glance.
- As a Tenant User, I want to create a bare metal instance by selecting a catalog item, providing a name, optionally providing an SSH public key and cloud-init user data, so that I can provision hardware through the console.
- As a Tenant User, I want to view instance details including state, error conditions, and a summary of my instance's configuration so that I can understand its current status and troubleshoot failures.
- As a Tenant User, I want to start or stop an instance so that I can control its power state without recreating the instance.
- As a Tenant User, I want to restart a running instance from the detail view so that I can recover from issues without deleting and reprovisioning.
- As a Tenant User, I want to delete an instance with a confirmation dialog so that I am protected from accidental deletion.

### Tenant Admin

- As a Tenant Admin, I want the same catalog browsing, instance creation, and lifecycle management capabilities as a Tenant User so that I can provision and manage bare metal instances for my organization.

### Cloud Provider Admin

Not affected by this feature. Catalog item management is out of scope for this tenant-facing UI.

### Cloud Infrastructure Admin

Not affected by this feature.

## Assumptions

- The BareMetalInstance fulfillment API (catalog item listing, instance creation, lifecycle operations) is available and functional before this UI work begins.
- Catalog items expose title and description; no hardware specification summary (CPU, memory, etc.) is available through the catalog item API.

## Dependencies

- **BareMetalInstance Fulfillment API:** The UI consumes the public fulfillment API for catalog item browsing, instance creation, state retrieval, and lifecycle operations (start, stop, restart, delete). The API must be available before UI work can be completed.