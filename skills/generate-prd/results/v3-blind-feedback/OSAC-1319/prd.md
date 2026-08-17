# BareMetal Instance UI

| Field       | Value   |
|-------------|---------|
| Author(s)   | Adrien Gentil |
| Jira        | [OSAC-1319](https://issues.redhat.com/browse/OSAC-1319) |
| Date        | 2026-08-10 |

## Problem Statement

Tenants have no web console support for bare metal instances. To browse available hardware profiles, provision a bare metal instance, or manage its lifecycle (power state, restart, deletion), tenants must use the API or CLI directly. This forces users who prefer click-ops to learn API tooling, slows adoption of BMaaS among self-service tenants, and creates an inconsistent experience that forces some workloads to require different tooling than others, fragmenting operator workflows.

## In Scope

- Tenant-facing UI screens only — catalog browsing, instance list, instance creation, and instance detail with lifecycle actions.
- The catalog browser renders item descriptions as formatted text, not raw markup.
- The instance list and detail views surface provisioning state and error details so tenants can track progress and troubleshoot failures.
- UI layout for the BareMetalInstance list is consistent with the existing ComputeInstance list.

## Out of Scope

- Cloud Provider Admin flows for managing catalog items and hardware profiles — admin-only via the private API.
- CLI or API changes — this feature adds UI screens that consume existing API endpoints.

## User Stories

### Tenant Admin / Tenant User

- As a Tenant Admin or Tenant User, I want to browse a read-only catalog of bare metal hardware profiles showing title, description rendered as formatted text, and key hardware specifications (such as CPU, memory, and storage) so that I can choose the right profile before provisioning.
- As a Tenant Admin or Tenant User, I want to create a bare metal instance by selecting a catalog item, optionally providing an SSH public key and cloud-init user data, and choosing whether the instance should start always-on or in a halted state so that I can provision hardware through the web console.
- As a Tenant Admin or Tenant User, I want the SSH public key field to be validated as OpenSSH format and the user data field to be limited to 64 KB so that I receive immediate feedback on input errors before submitting.
- As a Tenant Admin or Tenant User, I want to be taken to the instance detail view immediately after submitting a create request so that I can track provisioning progress without navigating manually.
- As a Tenant Admin or Tenant User, I want to view a list of my bare metal instances showing name, catalog item (as a link to the catalog item detail), state, and age so that I can monitor my fleet at a glance.
- As a Tenant Admin or Tenant User, I want to view instance details including state, error conditions, and a summary of the instance configuration so that I can understand the current configuration and diagnose failures.
- As a Tenant Admin or Tenant User, I want to change the power state of an instance between always-on and halted so that I can manage whether it is running without using the API.
- As a Tenant Admin or Tenant User, I want to restart a running instance from the detail view so that I can recover from issues without reprovisioning.
- As a Tenant Admin or Tenant User, I want to delete an instance with a confirmation dialog so that I am protected from accidental deletion.
- As a Tenant Admin or Tenant User, I want lifecycle actions (power state change, restart, delete) to be unavailable when the instance is in a transitional state (such as provisioning or deleting) so that I cannot trigger conflicting operations.

### Cloud Provider Admin

Not affected by this feature — catalog item management is out of scope.

### Cloud Infrastructure Admin

Not affected by this feature.

## Assumptions

- The BareMetal Instance fulfillment API endpoints (catalog items and instances) are available and stable before UI development begins.

## Dependencies

- **BareMetal Instance API (OSAC-1118):** Provides the fulfillment API endpoints for catalog items and instance lifecycle that the UI consumes. The API must be available before UI work can be completed.