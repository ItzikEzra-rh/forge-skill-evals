# DiskImage Resource for Disk Image Metadata Management

| Field       | Value   |
|-------------|---------|
| Author(s)   | Marc Sluiter |
| Jira        | [OSAC-2540](https://issues.redhat.com/browse/OSAC-2540) |
| Date        | 2026-08-10 |

## Problem Statement

ComputeInstances reference disk images via raw OCI artifact URLs, requiring users to know exact registry paths and tag formats before they can create a VM. There is no way to discover which images are available, and no metadata (OS family, architecture, description) to help users choose the right image. OS type must be specified per-instance rather than per-image, adding repetitive manual input and risking misconfiguration. Cloud Provider Admins and Tenant Admins have no way to control which images are available to tenants, prevent use of outdated images, or signal to users that an image is being retired. Without a managed image catalog, VM creation remains opaque and error-prone.

## In Scope

- DiskImage as a managed resource with human-readable metadata (title, description, optional icon, guest OS family, architecture) wrapping an existing OCI artifact reference.
- Two-tier visibility: global DiskImages managed by Cloud Provider Admins, tenant-scoped DiskImages managed by Tenant Admins.
- Image lifecycle management: active, deprecated (warns users but allows new VM creation), obsolete (blocks new VM creation), and reactivation back to active.
- Deletion protection: DiskImage deletion is blocked when referenced by active ComputeInstances, ComputeInstanceTemplates, or ComputeInstanceCatalogItems.
- Image source reference is immutable after DiskImage creation.
- Obsolete images are hidden from default listings and available via explicit filter.
- Removal of inline image fields from ComputeInstance and ComputeInstanceTemplate, replaced by a DiskImage reference. The per-instance OS type boolean is replaced by the guest OS family enum on DiskImage.
- ComputeInstanceTemplate and ComputeInstanceCatalogItem reference a DiskImage for image defaults.
- UI views: image list page, image detail page, image picker in VM creation flow, and lifecycle management controls.
- Users can see the lifecycle state of an image referenced by their ComputeInstance so they know when a referenced image has been deprecated or marked obsolete.
- API reference documentation as a required deliverable of this feature.

## Out of Scope

- Image binary upload through OSAC — DiskImages wrap existing OCI artifact references only.
- Image caching or performance optimization.
- VM snapshot or image export.
- Image scanning or CVE detection.
- Image versioning or tagging.
- `os_version` and minimum resource requirements fields — deferred.
- BareMetalInstance integration — covered by [OSAC-1270](https://issues.redhat.com/browse/OSAC-1270).
- Private registry authentication (pull credentials).
- Tenant Admin filtering of global images — all global images are visible to all tenants.
- Registry restriction for tenant admin image references.
- Installation changes.

## User Stories

### Cloud Provider Admin

- As a Cloud Provider Admin, I want to register a DiskImage with a title, description, guest OS family, and architecture so that tenants can discover and select it without knowing the raw OCI reference.
- As a Cloud Provider Admin, I want to list all registered DiskImages (global and tenant-scoped) so that I can audit what is available across the platform.
- As a Cloud Provider Admin, I want to update or delete a global DiskImage so that I can keep the catalog accurate, with deletion blocked when the image is referenced by active resources.
- As a Cloud Provider Admin, I want to deprecate a global DiskImage so that tenants are warned to migrate before it becomes unavailable.
- As a Cloud Provider Admin, I want to mark a global DiskImage as obsolete so that new VM creation with that image is blocked while existing VMs remain unaffected.
- As a Cloud Provider Admin, I want to reactivate a previously deprecated or obsolete DiskImage so that tenants can resume using it.
- As a Cloud Provider Admin, I want to reference a DiskImage in a ComputeInstanceTemplate so that VMs created from the template use an approved image by default.
- As a Cloud Provider Admin, I want to manage DiskImages through the UI console so that I can register, update, deprecate, and delete images without CLI or API tooling.

### Cloud Infrastructure Admin

Not affected by this feature.

### Tenant Admin

- As a Tenant Admin, I want to register tenant-scoped DiskImages for my organization so that my users can select from our approved images.
- As a Tenant Admin, I want to update or delete my tenant's DiskImages, with deletion blocked when referenced by active ComputeInstances, ComputeInstanceTemplates, or ComputeInstanceCatalogItems.
- As a Tenant Admin, I want to deprecate, mark obsolete, and reactivate my tenant's DiskImages so that I can manage my organization's image lifecycle.
- As a Tenant Admin, I want to reference a DiskImage in a ComputeInstanceCatalogItem so that VMs created from it use my organization's approved image by default.
- As a Tenant Admin, I want to manage my tenant's DiskImages through the UI console so that I can register, update, and delete images without CLI or API tooling.

### Tenant User

- As a Tenant User, I want to browse available DiskImages with metadata (title, description, guest OS family, architecture) so that I can choose the right image for my VM.
- As a Tenant User, I want to reference a DiskImage when creating a ComputeInstance so that the image source and OS type are resolved automatically.
- As a Tenant User, I want to see a deprecation warning when selecting a deprecated DiskImage so that I know to choose a different image.
- As a Tenant User, I want obsolete DiskImages hidden from the default image list, with the option to filter for them explicitly, so that I only see usable images by default.
- As a Tenant User, I want to browse and select DiskImages in the UI when creating a ComputeInstance so that I can choose the right image visually.
- As a Tenant User, I want to see the lifecycle state of the DiskImage referenced by my existing ComputeInstance so that I know when an image I am using has been deprecated or marked obsolete.

## Assumptions

- Guest OS family is an enumerated set (e.g., Linux, Windows) on the DiskImage rather than a free-text field.
- Architecture is a list of one or more values (e.g., amd64, arm64) on the DiskImage.

## Dependencies

- **OSAC-979 — VM Image Management:** DiskImage supersedes the ComputeImage resource proposed in OSAC-979. The existing enhancement proposal will be updated to reflect DiskImage once this PRD is approved.
- **OSAC-1270 — Base OS management for bare metal instances:** Downstream consumer — will extend DiskImage to BareMetalInstance after this feature lands. [Jira: OSAC-1270]