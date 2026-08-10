# GPU-Enabled InstanceTypes for ComputeInstances (MVP)

| Field       | Value   |
|-------------|---------|
| Author(s)   | Tzif Morgenshtern |
| Jira        | [OSAC-2917](https://issues.redhat.com/browse/OSAC-2917) |
| Date        | 2026-08-10 |

## Problem Statement

OSAC tenants running AI/ML workloads need GPU-equipped virtual machines but have no way to request GPU hardware through the self-service ComputeInstance flow. The InstanceType resource only models CPU cores, memory, and disk — there is no mechanism to express GPU requirements. Without GPU support, tenants must provision GPU workloads outside OSAC, bypassing tenant isolation and self-service workflows that the platform provides for CPU-based VMs.

## In Scope

- InstanceTypes extended with GPU type and GPU count, allowing Cloud Provider Admins to define GPU-enabled configurations alongside existing CPU/memory/disk specifications
- GPU-enabled ComputeInstances follow the same networking, storage, lifecycle model, and tenant isolation as non-GPU ComputeInstances
- GPU type is a free-text string with no platform-side validation — correctness is the Cloud Provider Admin's responsibility, consistent with how CPU and memory values are managed today
- Single VMaaS cluster — no cross-cluster GPU placement
- Tenant Users can see the current provisioning status and any failure reasons for GPU-enabled ComputeInstances

## Out of Scope

- GPU discovery API for programmatic detection of available GPU hardware — deferred to [OSAC-1839](https://issues.redhat.com/browse/OSAC-1839)
- Per-tenant GPU quotas — deferred to OSAC-1839
- MIG / vGPU partitioning support — deferred to OSAC-1839
- GPU VM live migration — deferred to OSAC-1839
- GPU-compatible boot image filtering — deferred to OSAC-1839
- Multi-cluster GPU placement — deferred to OSAC-1839
- GPU type validation against actual hardware — deferred to OSAC-1839
- Cost estimation and billing for GPU resources — deferred to OSAC-1839
- Preemptible VMs — deferred to OSAC-1839

## User Stories

### Cloud Provider Admin

- As a Cloud Provider Admin, I want to define InstanceTypes that include a GPU type and GPU count so that tenants can select GPU configurations when creating ComputeInstances.
- As a Cloud Provider Admin, I want to update or retire GPU-enabled InstanceTypes when the underlying GPU hardware changes so that the catalog reflects currently available hardware.

### Cloud Infrastructure Admin

Not affected by this feature.

### Tenant Admin

Not affected by this feature.

### Tenant User

- As a Tenant User, I want to see which InstanceTypes include GPU hardware when browsing available configurations so that I can choose the right InstanceType for my workload.
- As a Tenant User, I want to create a ComputeInstance using a GPU-enabled InstanceType so that my VM is provisioned with GPU hardware attached.
- As a Tenant User, I want GPU-enabled ComputeInstances to support the same lifecycle operations (start, stop, restart, delete) as non-GPU ComputeInstances so that I manage them the same way.
- As a Tenant User, I want to see the current provisioning status and any failure reasons for my GPU-enabled ComputeInstance so that I can track progress and troubleshoot issues.

## Assumptions

- GPU passthrough via KubeVirt is functional on the target VMaaS cluster — the Cloud Infrastructure Admin has configured the underlying host hardware and drivers before GPU-enabled InstanceTypes are offered to tenants. [Jira: OSAC-42]

## Dependencies

- **OSAC-42 (GPU passthrough plumbing):** Provides the infrastructure-level GPU passthrough capability that this feature relies on to attach GPU hardware to provisioned VMs. Must be in place before GPU-enabled InstanceTypes can be used.
- **OSAC-58 / OSAC-1205 (InstanceType GPU fields):** Extends the existing InstanceType resource with GPU type and count fields. This feature depends on those fields being available in the InstanceType definition.
