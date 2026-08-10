# Type-Safe Resource References

| Field       | Value   |
|-------------|---------|
| Author(s)   | Haim Tayrie |
| Jira        | [OSAC-1330](https://issues.redhat.com/browse/OSAC-1330) |
| Date        | 2026-08-10 |

## Problem Statement

When API users create or update resources that reference other resources (e.g., a cluster referencing a template, or an instance referencing a network), they must provide a raw string identifier with no indication of what type of object it refers to or whether it exists. Invalid or mistyped references are only caught at provisioning time — not at submission — leading to failed operations and difficult debugging. The API also cannot express whether a reference targets an object in the same tenant and project or in a different one, leaving cross-tenant reference semantics undocumented and inconsistently enforced. As OSAC migrates from ID-based identification to name-based identification (tenant, project, name), the lack of structured references makes it impossible to evolve reference fields without breaking every consumer.

## In Scope

- All resource types that are referenced by other resources gain structured, typed reference fields in the API — replacing raw string identifiers. This applies across all services (CaaS, BMaaS, VMaaS, Core).
- Two forms of reference per resource type: a full reference (for cross-tenant/cross-project targets) and a local reference (for same-tenant/same-project targets). The API designer determines which form is appropriate per field.
- References are validated at submission time: invalid references (nonexistent target, inconsistent identifiers) are rejected with descriptive errors before any provisioning begins.
- Backwards compatibility during the migration from ID-based to name-based identification — both forms are accepted during the transition, and the system auto-populates the missing form when one is provided.
- Existing API clients continue to work during the migration period; legacy ID-based references are accepted and resolved.

## Out of Scope

- Changes to the identity model itself (the migration from ID-based to name-based identification is a separate effort; this feature supports both during transition).
- UI-specific changes to reference selection workflows — the UI will consume the updated API but visual workflows for selecting referenced resources are not part of this scope.

## User Stories

### Cloud Provider Admin

- As a Cloud Provider Admin, I want references to shared resources (e.g., cluster templates available to all tenants) to carry explicit tenant and project context so that cross-tenant references are unambiguous and validated at submission time.

### Cloud Infrastructure Admin

- As a Cloud Infrastructure Admin, I want the API to reject requests that reference nonexistent resources (e.g., a network class or IP pool that does not exist) with a descriptive error so that I can correct mistakes before they cause provisioning failures.

### Tenant Admin

- As a Tenant Admin, I want to reference resources within my tenant and project by name alone so that I do not need to redundantly specify my own tenant and project on every API call.

### Tenant User

- As a Tenant User, I want the API to validate that referenced resources (e.g., a template, network, or security group) exist when I submit a request so that I receive immediate feedback instead of discovering errors at provisioning time.
- As a Tenant User, I want to provide either the legacy ID or the name of a referenced resource during the migration period so that my existing automation continues to work without immediate changes.

## Assumptions

- The set of resource types requiring typed references includes at minimum: ClusterTemplate, VirtualNetwork, Subnet, SecurityGroup, ComputeInstance, PublicIPPool, PublicIP, Tenant, ClusterOrder, and NetworkClass. Additional types may be identified during implementation.
- OSAC does not currently support in-place upgrades, so existing API clients will adopt the new reference format at redeployment time rather than through a live migration.

## Dependencies

- **Name-based identification migration:** The typed reference format is designed to support both ID-based and name-based identification during the transition. The eventual removal of the legacy ID field depends on completion of the broader migration to (tenant, project, name) identification.
