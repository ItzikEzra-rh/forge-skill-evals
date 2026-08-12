# GPU-Enabled InstanceTypes for ComputeInstances (MVP)

| Field       | Value   |
|-------------|---------|
| Author(s)   | Tzif Morgenshtern |
| Jira        | [OSAC-2917](https://issues.redhat.com/browse/OSAC-2917) |
| Date        | 2026-08-12 |

## Problem Statement

OSAC tenants need GPU-equipped virtual machines for AI/ML workloads, but ComputeInstances currently model only CPU cores, memory, and disk — there is no way to request GPU hardware. Tenants requiring GPU access must work outside the self-service platform, losing the networking, storage, and lifecycle benefits that ComputeInstances provide. Without GPU support, OSAC cannot serve AI/ML use cases, blocking adoption for tenants with GPU-dependent workloads.

## In Scope

- InstanceTypes extended with GPU type and GPU count as immutable fields, consistent with how CPU cores and memory are managed today — enabling Cloud Provider Admins to define GPU-enabled configurations alongside existing CPU/memory definitions
- GPU ComputeInstances follow the same lifecycle operations (start, stop, restart, delete), networking, storage, and tenant isolation model as non-GPU ComputeInstances
- GPU type is an admin-defined free-text string with no platform-side validation — correctness is the Cloud Provider Admin's responsibility, consistent with how CPU and memory values are managed today
- Single VMaaS cluster — no cross-cluster GPU placement
- Tenant Users can see which InstanceTypes include GPU hardware when browsing available configurations

## Out of Scope

- GPU discovery API (programmatic detection of available GPU hardware) — deferred to OSAC-1839
- Per-tenant GPU quotas — deferred to OSAC-1839
- MIG / vGPU partitioning — deferred to OSAC-1839
- Preemptible GPU VMs — deferred to OSAC-1839
- GPU VM live migration — deferred to OSAC-1839
- GPU-compatible boot image filtering — deferred to OSAC-1839
- Multi-cluster GPU placement — deferred to OSAC-1839
- GPU type validation — deferred to OSAC-1839
- Cost estimation and billing — deferred to OSAC-1839
- GPU clusters with InfiniBand interconnect — deferred to OSAC-1839

## User Stories

### Cloud Provider Admin

- As a Cloud Provider Admin, I want to create InstanceTypes that include a GPU type and GPU count so that tenants can select GPU-enabled configurations when creating ComputeInstances.
- As a Cloud Provider Admin, I want to delete GPU-enabled InstanceTypes when the underlying GPU hardware changes so that I can replace them with new InstanceTypes reflecting the updated configuration, since InstanceType fields are immutable.

### Cloud Infrastructure Admin

Not affected by this feature.

### Tenant Admin

Not affected by this feature.

### Tenant User

- As a Tenant User, I want to see which InstanceTypes include GPU hardware when browsing available configurations so that I can choose the right type for my workload.
- As a Tenant User, I want to create a ComputeInstance using a GPU-enabled InstanceType so that my VM is provisioned with GPU hardware attached.
- As a Tenant User, I want to see the current status of my GPU-enabled ComputeInstance so that I can track provisioning progress and troubleshoot issues.

## Assumptions

- GPU passthrough infrastructure is already configured on the underlying VMaaS cluster — this feature does not provision or configure GPU hardware on nodes. [Jira: OSAC-42]
- The GPU type that the Cloud Provider Admin enters in the InstanceType exists in the underlying system — the platform does not discover available GPUs or validate the GPU type value against actual hardware.

## Dependencies

- **OSAC-42 (GPU passthrough plumbing):** GPU passthrough support at the provisioning layer is already delivered. This feature builds on that foundation to expose GPU selection through InstanceTypes.
- **OSAC-58 / OSAC-1205 (InstanceType resource):** GPU fields extend the existing InstanceType resource. InstanceType CRUD must be available before GPU-enabled types can be created.