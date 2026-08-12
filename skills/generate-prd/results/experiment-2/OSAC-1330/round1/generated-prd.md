# Type-Safe Resource References

| Field       | Value   |
|-------------|---------|
| Author(s)   | Haim Tayrie |
| Jira        | [OSAC-1330](https://issues.redhat.com/browse/OSAC-1330) |
| Date        | 2026-08-12 |

## Problem Statement

When an API resource references another resource (e.g., a cluster referencing a template), the reference is a plain string field with no indication of what type of object it points to, what tenant or project it belongs to, or whether the target actually exists. API consumers must rely on documentation to know what a string field means, and invalid references are only caught deep in the provisioning flow rather than at request time. This lack of structure makes the API error-prone for all personas who create or update resources, and blocks the platform's migration from single-identifier lookup to structured (tenant, project, name) identification.

## In Scope

- **Typed reference model:** Replace all existing raw string reference fields across the API with structured, type-safe reference messages. Each reference message carries the target type explicitly in the schema, enabling compile-time validation for gRPC clients and schema-level clarity for REST consumers. A structured message approach is preferred over a URI/ARN-style single-string format because it conveys the type explicitly without requiring parsing or validation, while applications that prefer a string representation can easily build one from the structured fields.
- **Cross-scope and local references:** Support both cross-tenant/cross-project references (specifying tenant, project, and name) and same-tenant/same-project references (specifying name alone), so users operating within their own scope are not burdened with redundant identifiers.
- **Backwards-compatible identification:** Include a temporary id field alongside name-based identification in reference messages to support the migration period from id-based to (tenant, project, name)-based identification.
- **Existence validation at request time:** When a resource is created or updated, the system validates that all referenced objects exist and returns descriptive errors immediately if they do not.
- **Dangling reference protection:** When a referenced object is deleted, the system prevents the deletion or warns the user if existing resources still reference it, so that references do not silently become invalid after creation.
- **Consistent identifier resolution:** When a user provides a partial reference (e.g., id without name, or vice versa), the system resolves the missing field. When both are provided but conflict, the system rejects the request with a clear error.
- **Updated API documentation and OpenAPI specifications** reflecting the new reference types.
- **Test coverage** for reference validation, resolution, and dangling reference scenarios across resource types.

## Out of Scope

- Completion of the (tenant, project, name) migration itself — this feature adds the reference structure that enables migration, but the broader migration is tracked separately under [OSAC-1331](https://redhat.atlassian.net/browse/OSAC-1331).
- Changes to the CLI user experience — CLI commands will continue to accept identifiers and names as simple arguments (e.g., `--template my-template`); the typed reference structure is internal to the API layer.
- Changes to the UI console beyond what is driven by API contract changes.

## User Stories

### Any API Consumer

- As any API consumer (Cloud Provider Admin, Cloud Infrastructure Admin, Tenant Admin, or Tenant User), I want references between resources to carry the target type in the API schema, so that I can identify incorrect references through schema validation and tooling rather than consulting external documentation.
- As any API consumer, I want the API to reject a resource creation or update request immediately when a referenced object does not exist, so that I receive a clear error instead of discovering the problem during provisioning.
- As any API consumer, I want the system to auto-populate missing reference fields (e.g., fill in a name when I provide only an id, or vice versa), so that I can use whichever identifier I have available without manually looking up the other.
- As any API consumer, I want a clear error when I provide both an id and a name that refer to different objects, so that I can correct the mismatch before it causes unexpected behavior.

### Tenant Admin

- As a Tenant Admin, I want to reference resources in my own tenant and project by name alone, so that I do not need to specify tenant and project on every request within my own scope.

### Resource Owner

- As a resource owner, I want the system to prevent deletion of a resource that is still referenced by other resources (or warn me about dependent resources), so that references do not silently become dangling.

## Assumptions

- All existing resource types that are referenced by other resources have a unique name within their (tenant, project) scope, making name-based references unambiguous.
- The id field in reference messages is a transitional mechanism; once the platform completes the migration to (tenant, project, name) identification, the id field will be removed.
- The structured message approach provides sufficient usability for REST, gRPC, and CLI consumers without requiring an alternative URI/ARN-style format. REST consumers send a small JSON object (e.g., `{"template": {"name": "my-template"}}`) instead of a bare string, which does not meaningfully increase complexity.

## Dependencies

- **Resource identification migration ([OSAC-1331](https://redhat.atlassian.net/browse/OSAC-1331)):** The reference types are designed to support the transition from id-based to (tenant, project, name)-based identification. The migration effort depends on these reference types being in place first. The scope and timeline of the migration will be defined in its own PRD, which may be developed in parallel with this effort.