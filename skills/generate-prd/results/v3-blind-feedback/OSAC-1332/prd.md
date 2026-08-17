# CaaS Cluster Storage (v0.1)

| Field       | Value   |
|-------------|---------|
| Author(s)   | Akshay Nadkarni |
| Jira        | [OSAC-1332](https://issues.redhat.com/browse/OSAC-1332) |
| Date        | 2026-08-10 |

## Problem Statement

CaaS tenant clusters are provisioned without persistent storage. Tenant workloads cannot create PVCs until a CSI driver and StorageClasses are installed, requiring manual setup per cluster that creates operational burden and delays tenant workload availability. Cloud Provider Admins have no visibility into whether storage is available on a given cluster, making it impossible to distinguish compute readiness from storage readiness. Without this work, CaaS clusters cannot support stateful workloads, blocking adoption for any tenant requiring persistent storage.

The existing VAST storage provider also has gaps that make it unfit for CaaS use. Storage paths are keyed on mutable tenant names, meaning a tenant rename breaks existing volumes and risks data loss. CSI credentials are overprivileged, allowing the Tenant Manager to bypass Ansible-managed QoS controls and exposing the platform to unintended access. There is no provisioning target for CaaS clusters, so VAST cannot serve CaaS workloads at all. Until these gaps are closed, CaaS storage cannot be made reliable or secure.

## In Scope

- Automatic storage provisioning on CaaS clusters — when a cluster is provisioned and ready, the CSI driver and per-tenant, per-tier StorageClasses are installed without manual intervention
- Storage readiness tracked independently from compute readiness on the ClusterOrder, visible to Cloud Provider Admins
- Per-tenant, per-cluster, per-tier storage views created on the VAST storage backend
- The VAST storage backend is made CaaS-ready — storage paths use tenant UIDs to prevent breakage on rename, CSI credentials are scoped to least-privilege to prevent QoS bypass, and a CaaS provisioning target is added
- Storage resources on the cluster are cleaned up when the cluster is deleted
- A global VIP Pool is shared by all tenants for storage connectivity
- E2E validation against a live VAST cluster

## Out of Scope

- Per-tenant VIP Pools — all tenants share a single global VIP Pool in v0.1
- Tenant storage quotas or capacity management
- Storage support for VMaaS clusters — this feature targets CaaS only

## User Stories

### Cloud Provider Admin

- As a Cloud Provider Admin, I want persistent storage to be automatically available on CaaS clusters when they are ready so that I do not need to manually configure storage for each cluster.
- As a Cloud Provider Admin, I want to see storage readiness on a ClusterOrder independently from compute readiness so that I know when tenant workloads can consume persistent storage.
- As a Cloud Provider Admin, I want storage resources to be automatically removed when a CaaS cluster is deleted so that I do not need to manually clean up storage after cluster teardown.

### Cloud Infrastructure Admin

Not affected — VIP Pool pre-configuration is a prerequisite handled outside this feature's scope.

### Tenant Admin

Not affected by this feature.

### Tenant User

- As a Tenant User, I want to create PVCs using a StorageClass that matches my desired storage tier (e.g., fast, standard, archive) so that my workloads get the storage performance I need.

## Assumptions

- The VAST storage backend is reachable from the hub cluster and from CaaS tenant clusters.
- A global VIP Pool has been pre-configured by the Cloud Infrastructure Admin before CaaS clusters are provisioned with storage.

## Dependencies

- **CaaS cluster provisioning (ClusterOrder):** Storage provisioning is triggered after a CaaS cluster reaches its ready state. The ClusterOrder lifecycle must be functional before storage can be installed.