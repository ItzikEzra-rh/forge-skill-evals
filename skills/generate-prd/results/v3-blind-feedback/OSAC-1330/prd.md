# Type-Safe Resource References

| Field       | Value   |
|-------------|---------|
| Author(s)   | Haim Tayrie |
| Jira        | [OSAC-1330](https://issues.redhat.com/browse/OSAC-1330) |
| Date        | 2026-08-10 |

## Problem Statement

When API users create or update resources that reference other resources (e.g., a cluster referencing a template, or an instance referencing a network), they must provide a raw string identifier with no indication of what type of object it refers to or whether it exists. Invalid or mistyped references are only caught at provisioning time — not at submission — leading to failed operations and difficult debugging. The API also cannot express whether a reference targets an object in the same tenant and project or in a different one, leaving cross-tenant reference semantics undocumented and inconsistently enforced. As OSAC migrates from ID-based to name-based identification, reference fields cannot evolve without breaking every existing API consumer, making the migration path unmanageable.

## In Scope

- All resource types that are referenced by other resources gain structured, typed reference fields in the API — replacing raw string identifiers. This applies across all services (CaaS, BMaaS, VMaaS, Core).
- Two forms of reference per resource type: a full reference (for cross-tenant/cross-project targets) and a local reference (for same-tenant/same-project targets). The API designer determines which form is appropriate per field.
- References are validated at submission time: invalid references (nonexistent target, inconsistent identifiers) are rejected with descriptive errors before any provisioning begins.
- When a request provides both a legacy ID and a name for a referenced resource, the API validates that they refer to the same object and rejects the request with a descriptive error if they are inconsistent.
- Reference validation and resolution is enforced as a cross-cutting capability across all services, so that no per-service custom logic is required to validate or resolve references.
- During the migration period, clients that provide only an ID or only a name for a referenced resource will receive a valid, consistent response — the API resolves the reference fully without requiring the client to supply both.
- Existing API clients continue to work during the migration period; legacy ID-based references are accepted and resolved.
- API documentation and OpenAPI specifications are updated to reflect the new reference message types, replacing documentation of raw string fields.

## Out of Scope

- Changes to the identity model itself (the migration from ID-based to name-based identification is a separate effort; this feature supports both during transition).
- Removal of legacy ID fields from reference messages — this will be decided as part of the name-based identification migration effort.
- UI-specific changes to reference selection workflows — the UI will consume the updated API but visual workflows for selecting referenced resources are not part of this scope.

## User Stories

### Cloud Provider Admin

- As a Cloud Provider Admin, I want references to shared resources (e.g., cluster templates available to all tenants) to carry explicit tenant and project context so that cross-tenant references are unambiguous and validated at submission time.

### Cloud Infrastructure Admin

- As a Cloud Infrastructure Admin, I want to be able to audit which resources are referenced by which other resources across tenants so that I can safely modify or retire infrastructure resources without causing silent failures.

### Tenant Admin

- As a Tenant Admin, I want to reference resources within my tenant and project by name alone so that I do not need to redundantly specify my own tenant and project on every API call.

### Tenant User

- As a Tenant User, I want the API to validate that referenced resources (e.g., a template, network, or security group) exist when I submit a request so that I receive immediate feedback instead of discovering errors at provisioning time.
- As a Tenant User, I want to provide either the legacy ID or the name of a referenced resource during the migration period so that my existing automation continues to work without immediate changes.
- As a Tenant User, I want the API to reject my request with a descriptive error if the ID and name I provide for a referenced resource do not refer to the same object, so that I can detect and correct conflicting values before they cause failures.

## Assumptions

- The set of resource types requiring typed references includes at minimum: ClusterTemplate, VirtualNetwork, Subnet, SecurityGroup, ComputeInstance, PublicIPPool, PublicIP, Tenant, ClusterOrder, and NetworkClass. Additional types may be identified during implementation.
- OSAC does not currently support in-place upgrades, so existing API clients will adopt the new reference format at redeployment time rather than through a live migration.
- The removal of legacy ID fields from reference messages is out of scope for this feature and will be decided as part of the name-based identification migration effort.

## Dependencies

- **Name-based identification migration:** Completion of this feature is coordinated with the broader name-based identification migration. Legacy ID-based references will continue to be accepted until that migration is complete, at which point ID fields may be removed.