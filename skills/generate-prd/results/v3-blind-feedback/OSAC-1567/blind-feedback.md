## PRD Review: OSAC-1567 — Secret Management

---

### Issue 1 — Completeness: Missing `SecretClass` scope item

- **Category**: completeness
- **Severity**: important
- **Problem**: The Jira Definition of Done explicitly calls out a `SecretClass` type for pluggable backends as a distinct deliverable. The PRD's In Scope section collapses this into a general statement about "pluggable secret backends" without surfacing `SecretClass` as a named concept. Readers cannot trace the DoD item to the PRD.
- **Fix**: Add a dedicated bullet to In Scope: "A `SecretClass` resource type that defines and configures available secret backends (database, hub/Kubernetes), allowing administrators to select and configure storage strategies independently of individual secrets."

---

### Issue 2 — Completeness: Missing Envelope Encryption specifics

- **Category**: completeness
- **Severity**: minor
- **Problem**: The Jira DoD calls out envelope encryption (RSA + AES) as an explicit deliverable. The PRD In Scope says "envelope encryption" but drops the algorithm pair. While full algorithm specification risks design leakage, the *concept* that two-layer encryption is used (wrapping key + data key) is a meaningful scope signal that differentiates this from simple field-level encryption. Omitting it leaves the scope ambiguous.
- **Fix**: Retain "envelope encryption" but clarify in one phrase that it uses a wrapping-key/data-key scheme — e.g., "envelope encryption (a wrapping key protects per-secret data keys) for database-backed secrets" — without naming RSA/AES.

---

### Issue 3 — Problem Statement: Contains solution language

- **Category**: problem-statement
- **Severity**: important
- **Problem**: The sentence "Retrieving secrets requires ad-hoc, per-resource RPCs (e.g., GetKubeconfig, GetPassword) with no uniform access pattern, **forcing every consuming service to implement its own retrieval mechanism**" shifts from describing the pain to implying the solution shape (a uniform mechanism). Similarly, the final sentence "every new secret type requires bespoke API and access-control work" is borderline — it describes operational cost but nudges toward the solution.
- **Fix**: Reframe to pure pain: "There is no uniform access pattern for secret retrieval; each consuming service must independently implement ad-hoc retrieval logic, increasing the cost and risk surface of every new secret type." Remove any forward reference to what a solution would look like.

---

### Issue 4 — Persona Alignment: Cloud Provider Admin story is misaligned

- **Category**: personas
- **Severity**: important
- **Problem**: The Cloud Provider Admin story ("I want to select between database-backed storage and hub (Kubernetes) secret backends so that I can match the secret storage strategy to my infrastructure requirements") describes a capability that is infrastructure/platform configuration, which per OSAC conventions belongs to the **Cloud Infrastructure Admin** persona. Cloud Provider Admin manages the offering of compute/cloud resources to tenants, not internal platform storage topology decisions. The Jira user story uses "Cloud Provider Admin" but the capability is an infra-ops concern.
- **Fix**: Reassign this story to Cloud Infrastructure Admin and revise the Tenant Admin or Cloud Provider Admin section to include a story genuinely within CPA's remit (e.g., ensuring secrets scoped to provider-managed resources are accessible within their provider boundary), or explicitly note "Cloud Provider Admin: Not affected by this feature" if no authentic story exists.

---

### Issue 5 — Personas: Tenant Admin story is thin and doesn't reflect the full scope

- **Category**: personas
- **Severity**: minor
- **Problem**: The Tenant Admin story covers only IdP client secrets. The Jira describes org config credentials broadly, and the scope includes full CRUD for secrets. The story should reflect that Tenant Admins manage the full lifecycle of org-scoped secrets (create, update, delete, audit), not just storage.
- **Fix**: Broaden: "As a Tenant Admin, I want to create, update, and delete secrets scoped to my organization — including IdP client secrets and storage credentials — through a dedicated secrets API so that sensitive credentials have a consistent, auditable lifecycle separate from the resources that consume them."

---

### Issue 6 — Completeness: No story or scope item for access control / tenant isolation

- **Category**: completeness
- **Severity**: important
- **Problem**: OPA policies for secret access control and tenant isolation appear in In Scope as a bullet, but no user story surfaces the *user-facing value* of that control. Access control is a DoD item in the Jira and a meaningful concern for both Tenant Admins (my secrets are isolated from other tenants) and Cloud Infrastructure Admins (platform-wide policy enforcement). Without a story, it reads as an implementation checkbox.
- **Fix**: Add a Tenant Admin story: "As a Tenant Admin, I want access to secrets strictly scoped to my organization so that credentials I store cannot be read by users in other tenants." Optionally add a CIA story for platform-wide policy enforcement.

---

### Issue 7 — Template: `Dependencies` section references OSAC-1337 is omitted

- **Category**: completeness
- **Severity**: minor
- **Problem**: The Jira Related section lists OSAC-1337 as the implementation epic. While implementation epics don't always belong in PRDs, OSAC-1330 is correctly listed as a dependency. If OSAC-1337 is the implementation tracker, it warrants at least acknowledgment so readers know where to find the work breakdown.
- **Fix**: Either add OSAC-1337 to the Dependencies section with a note ("implementation epic, no PRD dependency") or explicitly omit it with a comment — don't silently drop related issues that are called out in the Jira.

---

### Issue 8 — Design Leakage: `GetKubeconfig` and `GetPassword` RPC names in Problem Statement

- **Category**: design-leakage
- **Severity**: minor
- **Problem**: Naming specific internal RPC methods (`GetKubeconfig`, `GetPassword`) in the Problem Statement leaks current implementation vocabulary into a requirements document. The problem is "inconsistent retrieval mechanisms," not the specific RPC names.
- **Fix**: Replace with "per-resource retrieval operations" or "resource-specific credential retrieval calls" without naming internal method signatures.

---

### Summary

The PRD is structurally sound and covers the majority of the Jira scope. The most important fixes are: (1) realigning the Cloud Provider Admin persona story, (2) adding an access-control/tenant-isolation user story, (3) surfacing `SecretClass` explicitly in scope, and (4) removing solution language and internal RPC names from the Problem Statement. No extraneous sections beyond the allowed template were found. Async status is not a concern here as secrets are synchronous CRUD resources.