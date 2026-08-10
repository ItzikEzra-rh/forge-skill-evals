# BareMetal Instance UI

| Field       | Value   |
|-------------|---------|
| Author(s)   | Adrien Gentil |
| Jira        | [OSAC-1319](https://issues.redhat.com/browse/OSAC-1319) |
| Date        | 2026-08-10 |

## Problem Statement

Tenants have no web console support for bare metal instances. To browse available hardware profiles, provision a bare metal instance, or manage its lifecycle (power state, restart, deletion), tenants must use the API or CLI directly. This forces users who prefer click-ops to learn API tooling, slows adoption of BMaaS among self-service tenants, and creates an inconsistent experience compared to ComputeInstance, which already has full UI coverage.

## In Scope

- Tenant-facing UI screens only — catalog browsing, instance list, instance creation, and instance detail with lifecycle actions.
- The instance list and detail views surface provisioning state and error details so tenants can track progress and troubleshoot failures.
- UI layout for the BareMetalInstance list is consistent with the existing ComputeInstance list.

## Out of Scope

- Cloud Provider Admin flows for managing catalog items and hardware profiles — admin-only via the private API.
- CLI or API changes — this feature adds UI screens that consume existing API endpoints.

## User Stories

### Tenant Admin / Tenant User

- As a Tenant Admin or Tenant User, I want to browse a read-only catalog of bare metal hardware profiles showing title, description, and hardware summary so that I can choose the right profile before provisioning.
- As a Tenant Admin or Tenant User, I want to create a bare metal instance by selecting a catalog item, optionally providing an SSH public key and cloud-init user data, and choosing a run strategy (always on or halted) so that I can provision hardware through the web console.
- As a Tenant Admin or Tenant User, I want the SSH public key field to be validated as OpenSSH format and the user data field to be limited to 64 KB so that I receive immediate feedback on input errors before submitting.
- As a Tenant Admin or Tenant User, I want to view a list of my bare metal instances showing name, catalog item, state, and age so that I can monitor my fleet at a glance.
- As a Tenant Admin or Tenant User, I want to view instance details including state, error conditions, spec summary (catalog item, run strategy, SSH key and user data presence) so that I can understand the current configuration and diagnose failures.
- As a Tenant Admin or Tenant User, I want to toggle the run strategy between always-on and halted on an instance so that I can manage its power state without using the API.
- As a Tenant Admin or Tenant User, I want to restart a running instance from the detail view so that I can recover from issues without reprovisioning.
- As a Tenant Admin or Tenant User, I want to delete an instance with a confirmation dialog so that I am protected from accidental deletion.

### Cloud Provider Admin

Not affected by this feature — catalog item management is out of scope.

### Cloud Infrastructure Admin

Not affected by this feature.

## Assumptions

- The BareMetal Instance fulfillment API endpoints (catalog items and instances) are available and stable before UI development begins.

## Dependencies

- **BareMetal Instance API (OSAC-1118):** Provides the fulfillment API endpoints for catalog items and instance lifecycle that the UI consumes. The API must be available before UI work can be completed.
