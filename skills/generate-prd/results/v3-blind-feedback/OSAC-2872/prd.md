# OSAC Storage Control Plane

| Field       | Value   |
|-------------|---------|
| Author(s)   | Akshay Nadkarni |
| Jira        | [OSAC-2872](https://redhat.atlassian.net/browse/OSAC-2872) |
| Date        | 2026-08-10 |

## Problem Statement

CaaS tenant clusters have no vendor-abstracted storage layer. Tenants who need persistent storage must interact with vendor-specific StorageClasses that expose backend addresses and vendor details — breaking tenant isolation and creating a risk of vendor credential exposure and cross-tenant data access. There is no enforcement point for per-tenant storage policy, no credential isolation, and no central record of what volumes exist or which tenant owns them. Without a storage control plane, OSAC cannot offer block storage as a platform service, blocking any tenant workload that requires persistent storage on CaaS clusters.

## In Scope

- Tenants consume block storage through opaque storage tiers — no vendor details, credentials, or backend addresses are exposed to tenant clusters.
- Multiple storage vendors (NetApp ONTAP, VAST, Pure Storage) are supported through a single, uniform storage interface on each tenant cluster.
- Per-tenant policy enforcement: authorization and tier access are checked before every volume operation.
- Vendor credentials are never stored on or accessible from tenant clusters.
- Every volume is tracked in a central inventory with tenant, tier, state, size, and attachment information through its full lifecycle.
- A private volume management API is available to internal OSAC services for creating, retrieving, listing, and deleting volume records, supporting future integration with tenant-facing volume management.
- Storage is automatically deployed and configured on tenant clusters when they are provisioned, and storage provisioning on tenant clusters is secured so that only the authorized cluster can initiate volume operations on behalf of its tenants.
- Tenants and admins can see whether storage is ready on a given cluster.

## Out of Scope

- Public tenant-facing Volume API and UI integration for volume management — covered by [OSAC-984](https://redhat.atlassian.net/browse/OSAC-984).
- Storage quota lifecycle (reserve/commit/release pattern and stale reservation cleanup) — deferred to a future milestone.
- VMaaS and BMaaS storage integration (ComputeInstance/DataVolume and BareMetalInstance storage provisioning) — deferred to separate features.
- CSI certification and conformance testing (csi-test sanity suite, Kubernetes E2E storage tests, OLM operator bundle) — deferred to a separate feature.
- Audit logging of storage policy decisions and volume operations — deferred to a separate feature.
- Storage metering.
- Vendor REST adapters for non-CSI volume management — deferred; may be addressed alongside [OSAC-984](https://redhat.atlassian.net/browse/OSAC-984).

## User Stories

### Cloud Infrastructure Admin

- As a Cloud Infrastructure Admin, I want to configure storage backends and tiers so that tenant clusters can consume block storage from the appropriate vendor without tenants seeing vendor details.
- As a Cloud Infrastructure Admin, I want to define which storage tiers are available to which tenants so that storage access is governed by policy.
- As a Cloud Infrastructure Admin, I want to verify that storage is successfully deployed and ready on any tenant cluster so that I can confirm provisioning completed correctly before tenants use it.

### Cloud Provider Admin

- As a Cloud Provider Admin, I want to see the volume inventory across all tenants — including tenant, tier, state, size, and attachment information — so that I can track storage consumption and attribution.
- As a Cloud Provider Admin, I want volume records to expose the full lifecycle state (creating, available, attached, detached, deleting, deleted) so that I can accurately track and audit storage consumption across the platform.
- As a Cloud Provider Admin, I want to see whether storage is ready on any tenant cluster so that I can verify successful deployment.

### Tenant Admin

- As a Tenant Admin, I want to see which storage tiers are available to my organization so that I can plan workload placement.

### Tenant User

- As a Tenant User, I want to request persistent storage for my workload using my cluster's available storage tiers so that my workload has durable storage without needing to know the underlying vendor or backend.
- As a Tenant User, I want to see whether storage is available and ready on my cluster so that I know when I can create persistent volumes.
- As a Tenant User, I want volumes to be cleaned up on the backend when I delete a persistent volume claim so that storage is properly released.

## Assumptions

- At least one storage vendor (NetApp ONTAP, VAST, or Pure Storage) is reachable from the hub cluster and has been configured by a Cloud Infrastructure Admin before tenants can provision volumes.
- Vendor node plugins are available on tenant clusters for mount operations to be performed locally without requiring calls back to the storage control plane.
- Tenant clusters run OpenShift/Kubernetes with standard CSI sidecar support (external-provisioner, external-attacher).
- The storage control plane on the hub cluster is network-reachable from tenant cluster nodes.

## Dependencies

- **ClusterOrder provisioning:** Storage deployment on tenant clusters is triggered as part of the cluster provisioning lifecycle. ClusterOrder provisioning must be functional before automated storage deployment can occur.