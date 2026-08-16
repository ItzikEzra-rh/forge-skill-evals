# Judge Feedback -- Issues to Fix

## Template Compliance (PARTIAL, scored 1/2)

All required sections are present but the YAML frontmatter has a formatting error (nested yaml fences with a duplicate '---') and 'authors' contains 'TBD' rather than a real author, though the fields themselves exist.

Evidence:
- ```yaml
---
title: secret-management
authors:
  - TBD
- tracking-link:
  - https://redhat.atlassian.net/browse/OSAC-1567
- prd:
  - "prd.md"

## Proto Schema Quality (PARTIAL, scored 1/2)

The generated document contains proto code blocks with standard OSAC object shape (id, Metadata, SecretSpec, SecretStatus, conditions), gRPC service with full CRUD, REST transcoding, and gRPC error codes, but differs from gold standard's simpler `map<string, bytes> data` structure with dual-backend approach, and adds a `SecretStatus` with conditions that the gold standard omits entirely.

Evidence:
- message Secret { string id = 1; Metadata metadata = 2; SecretSpec spec = 3; SecretStatus status = 4; }
- service SecretService { rpc CreateSecret...rpc GetSecret...rpc ListSecrets...rpc UpdateSecret...rpc DeleteSecret
- message SecretSpec { string display_name = 1; SecretType type = 2; bytes payload = 3;

## Implementation Depth (FAIL, scored 1/2)

The generated document has significant implementation depth but misses critical specifics present in the gold standard: it lacks the dual-backend (Vault + Hub) architecture, the detailed per-tenant JWT forwarding auth mechanism with Keycloak brokering, the specific token caching strategy (by JWT jti + tenant), the credential migration binary's idempotency logic, and the concrete Vault namespace structure with per-namespace KV v2 and JWT auth mounts.

Evidence:
- Two secret backends exist for 0.2: Vault ... Hub
- cached by JWT `jti` + tenant name; evicted at the earlier of JWT expiry or Vault token TTL
- bound_claims: {"organization": ["<tenant_name>"]}` to enforce that the user belongs to the tenant

## Workflow Completeness (FAIL, scored 1/2)

The generated document covers all four lifecycle operations and basic error paths but lacks the Mermaid sequence diagram the gold standard requires, and does not define actors using OSAC personas in workflow steps (e.g., 'Cloud Infrastructure Admin: Configure the Secret Store' is absent), nor does it cover the Hub backend workflow or tenant namespace lifecycle as distinct workflow sections.

Evidence:
- Workflow 1 — Tenant User creates a self-service secret
- Workflow 3 — Automatic secret creation during resource provisioning
- #### Error Flows

## Failure Handling (FAIL, scored 1/2)

The generated document covers several concrete failure modes with good detail (Vault unreachable, DB commit failure, concurrent update conflict, token expiry, controller restart) but misses gold-standard-specific failures like tenant namespace not yet existing returning FAILED_PRECONDITION, Keycloak token exchange failures, and Hub-backend specific failure distinctions, while the gold standard's per-operation table is more systematic about distinguishing public vs private API and Hub vs Vault backend failures.

Evidence:
- Namespace missing: `FAILED_PRECONDITION`. Auth or Vault failure: no record created.
- Vault token expired during operation | Vault SDK returns 403 | `[Assumption]` — fulfillment-service re-authenticates
- Controller restart mid-creation | Operator re-reconciles; calls `CreateSecret` again with idempotent display_name

## Content Completeness (FAIL, scored 1/2)

The generated document covers core concepts (Secret resource, Vault backend, PostgreSQL metadata-only storage, tenant isolation) but misses several substantive elements from the gold standard: dual-backend architecture (Hub backend for system-created Kubernetes secrets is absent), the specific JWT forwarding/Keycloak token exchange auth model, credential migration binary details, the specific credential reference fields across multiple resources (Hub, IdentityProvider, StorageBackend, Tenant), project-scoped secrets, the namespace-per-tenant Vault model with child namespaces, and the deprecation/removal of GetKubeconfig/GetPassword RPCs.

Evidence:
- Two secret backends exist for 0.2: Vault... Hub — system-created secrets whose data lives in Kubernetes Secrets on hub clusters
- GetKubeconfig and GetPassword RPCs are deprecated then removed
- A Go binary moves existing inline credentials into the Secrets API

## Scope Discipline (FAIL, scored 0/2)

The generated document introduces significant scope creep (token caching, immutable field triggers, detailed error code tables, orphan cleanup reconciler, detailed RBAC permission matrix) and reduces scope by omitting critical PRD requirements present in the gold standard: the Hub backend for system-created secrets, the Vault namespace-based tenant isolation model, Keycloak JWT forwarding/token exchange auth architecture, credential migration binary, CLI --from-file conventions, Secret Labels convention, and the GetKubeconfig/GetPassword deprecation.

Evidence:
- Two secret backends exist for 0.2: Vault... Hub
- bound_claims: {"organization": ["<tenant>"]}" to enforce tenant
- GetKubeconfig and GetPassword RPCs are deprecated then removed

