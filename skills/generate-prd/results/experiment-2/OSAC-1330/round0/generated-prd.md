# Type-Safe Resource References

| Field       | Value   |
|-------------|---------|
| Author(s)   | Haim Tayrie |
| Jira        | [OSAC-1330](https://issues.redhat.com/browse/OSAC-1330) |
| Date        | 2026-08-12 |

## Problem Statement

When an API resource references another resource (e.g., a cluster referencing a template), the reference is a plain string field with no indication of what type of object it points to, what tenant or project it belongs to, or whether the target actually exists. API consumers must rely on documentation to know what a string field means, and invalid references are only caught deep in the provisioning flow rather than at request time. This lack of structure makes the API error-prone for all personas who create or update resources, and blocks the platform's migration from single-identifier lookup to structured (tenant, project, name) identification.

## In Scope

- Typed reference messages for each resource type, supporting both cross-tenant/cross-project references and same-tenant/same-project (local) references.
- Backwards-compatible id field in reference messages to support the migration from id-based to (tenant, project, name)-based identification; the id field is temporary and will be removed after migration completes.
- Replacement of all existing raw string reference fields across the API with the new typed reference messages.
- Automatic server-side validation that referenced objects exist, with descriptive errors when they do not.
- Automatic resolution of partial references: when a user provides an id but not a name (or vice versa), the system fills in the missing field — and rejects the request if both are provided but conflict.
- Updated API documentation and OpenAPI specifications reflecting the new reference types.
- Test coverage for reference validation and resolution across resource types.

## Out of Scope

- Completion of the (tenant, project, name) migration itself — this feature adds the reference structure that enables migration, but the broader migration is a separate effort.
- Changes to the UI console or CLI beyond what is driven by API contract changes.

## User Stories

### Cloud Provider Admin

- As a Cloud Provider Admin, I want the API to reject a resource creation request immediately when a referenced object (e.g., a cluster template or public IP pool) does not exist, so that I receive a clear error instead of discovering the problem during provisioning.

### Cloud Infrastructure Admin

- As a Cloud Infrastructure Admin, I want references between infrastructure resources (e.g., a NetworkClass referenced by a VirtualNetwork) to carry the target type in the API schema, so that I can identify incorrect references without consulting external documentation.

### Tenant Admin

- As a Tenant Admin, I want to reference resources in my own tenant and project by name alone (local reference), so that I do not need to specify tenant and project on every request within my own scope.

### Tenant User

- As a Tenant User, I want the system to auto-populate missing reference fields (e.g., fill in a name when I provide only an id, or vice versa), so that I can use whichever identifier I have available without manually looking up the other.
- As a Tenant User, I want a clear error when I provide both an id and a name that refer to different objects, so that I can correct the mismatch before it causes unexpected behavior.

## Assumptions

- All existing resource types that are referenced by other resources have a unique name within their (tenant, project) scope, making name-based references unambiguous.
- The id field in reference messages is a transitional mechanism; once the platform completes the migration to (tenant, project, name) identification, the id field will be removed without a further deprecation cycle.

## Dependencies

- **Resource identification migration:** The reference types are designed to support the transition from id-based to (tenant, project, name)-based identification. The migration effort depends on these reference types being in place first.
