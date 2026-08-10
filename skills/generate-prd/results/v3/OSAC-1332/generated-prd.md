# CaaS Cluster Storage (v0.1)

| Field       | Value   |
|-------------|---------|
| Author(s)   | Akshay Nadkarni |
| Jira        | [OSAC-1332](https://issues.redhat.com/browse/OSAC-1332) |
| Date        | 2026-08-10 |

## Problem Statement

CaaS tenant clusters are provisioned without persistent storage. Tenant workloads cannot create PVCs until a CSI driver and StorageClasses are manually installed, and there is no automation to do this after cluster provisioning. Cloud Provider Admins have no visibility into whether storage is available on a given cluster, making it impossible to distinguish compute readiness from storage readiness. Without this work, CaaS clusters cannot support stateful workloads, blocking adoption for any tenant requiring persistent storage.

## In Scope

- Automatic storage provisioning on CaaS clusters — when a cluster is provisioned and ready, the CSI driver and per-tenant, per-tier StorageClasses are installed without manual intervention
- Storage readiness tracked independently from compute readiness on the ClusterOrder, visible to Cloud Provider Admins
- Per-tenant, per-cluster, per-tier storage views created on the VAST storage backend
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

### Cloud Infrastructure Admin

Not affected by this feature.

### Tenant Admin / Tenant User

- As a Tenant Admin or Tenant User, I want to create PVCs using a StorageClass that matches my desired storage tier (e.g., fast, standard, archive) so that my workloads get the storage performance I need.
- As a Tenant Admin or Tenant User, I want to see whether storage is ready on my CaaS cluster so that I know when I can provision persistent volumes.

## Assumptions

- The VAST storage backend is reachable from the hub cluster and from CaaS tenant clusters.
- A global VIP Pool has been pre-configured by the Cloud Infrastructure Admin before CaaS clusters are provisioned with storage.

## Dependencies

- **CaaS cluster provisioning (ClusterOrder):** Storage provisioning is triggered after a CaaS cluster reaches its ready state. The ClusterOrder lifecycle must be functional before storage can be installed.
