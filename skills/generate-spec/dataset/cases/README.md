# Design Creator Evaluation Dataset

This directory contains evaluation cases for the design-creator tool. Each case represents a real OSAC enhancement with its original PRD and design documents from the enhancement-proposals repository.

## Dataset Overview

| Case | Jira Key | Title | Score | Lines | Type |
|------|----------|-------|-------|-------|------|
| case-001 | OSAC-1567 | Secret Management | 7/8 | 901 | Backend API + Security |
| case-002 | OSAC-1425 | Networking UI (VMaaS scope) | 7/8 | 882 | Frontend UI |
| case-003 | OSAC-1110 | StorageTier API | 7/8 | 534 | Backend API |
| case-004 | OSAC-1269 | ClusterVersion API | 6/8 | 459 | Backend API |
| case-005 | OSAC-1332 | CaaS Cluster Storage | 6/8 | 364 | Controller + AAP |
| case-006 | OSAC-1319 | BareMetal Instance UI | 6/8 | 325 | Frontend UI |

## Case Structure

Each case directory contains:

- **input.yaml** - Minimal input required to run the design-creator (jira_key, title, priority)
- **annotations.yaml** - Expected evaluation results and metadata
  - `expected_score`: Quality score out of 8
  - `expected_pass`: Whether the design should pass quality threshold
  - `gold_design_path`: Path to original design.md in enhancement-proposals
  - `notes`: Brief description and key characteristics
- **gold-design.md** - Copy of the actual design.md from enhancement-proposals (reference output)
- **gold-prd.md** - Copy of the actual prd.md from enhancement-proposals (reference input)

## Case Selection Rationale

Cases were selected to provide:

1. **Score diversity** - Range from 6/8 (passing) to 7/8 (high quality)
2. **Design length diversity** - From 325 to 901 lines
3. **Type diversity** - Mix of backend API, frontend UI, controller, and AAP designs
4. **Complexity diversity** - From focused API additions to cross-component integrations

## Usage

To run evaluation on a case:

```bash
cd /home/ercohen/go/src/github/eranco74/osac-workspace/design-creator
python -m design_creator.eval.run --case eval/dataset/cases/case-001-osac-1567-secret-management
```

To run full dataset evaluation:

```bash
python -m design_creator.eval.run --dataset eval/dataset/cases
```

## Design Quality Scoring

Designs are scored out of 8 points based on:

1. **Completeness** (2 points) - All required sections present with substantive content
2. **Technical Accuracy** (2 points) - Correct use of OSAC patterns, APIs, and conventions
3. **Clarity** (1 point) - Clear problem statement, motivation, and solution approach
4. **Implementation Detail** (1 point) - Sufficient detail for implementation (code structure, file organization, API schemas)
5. **Testing Coverage** (1 point) - Unit, integration, and E2E test plans
6. **Integration Analysis** (1 point) - Cross-component dependencies and deployment considerations

Passing threshold: 5/8

## Case Details

### case-001: OSAC-1567 Secret Management (7/8)
High-quality design introducing encrypted secret storage with Vault backend. Comprehensive security architecture, API design, and multi-backend support. Strong integration analysis with existing credential systems.

### case-002: OSAC-1425 Networking UI (7/8)
Well-structured UI design following React 19 and PatternFly 6 patterns. Comprehensive wizard integration for inline networking resource creation. Good coverage of list/detail/form patterns.

### case-003: OSAC-1110 StorageTier API (7/8)
Clean private API design for storage tier management with QoS properties. Strong integration with StorageBackend system and tenant onboarding workflow. Provider-neutral abstraction.

### case-004: OSAC-1269 ClusterVersion API (6/8)
Focused API design for managing cluster versions with lifecycle states. Clean abstraction over OpenShift release images. Good foundation for future upgrade workflows.

### case-005: OSAC-1332 CaaS Cluster Storage (6/8)
Controller design extending storage provisioning to CaaS clusters. Integration with AAP and HyperShift APIs. Clear multi-stage provisioning flow.

### case-006: OSAC-1319 BareMetal Instance UI (6/8)
UI design reusing existing catalog and wizard patterns for bare metal instance management. Good pattern consistency with VM provisioning UI.

## Dataset Maintenance

This dataset is based on enhancement-proposals as of 2026-07-24. To update:

1. Re-run the discovery script to find new high-quality designs
2. Copy updated design.md and prd.md files from enhancement-proposals
3. Re-score designs if evaluation criteria change
4. Update annotations.yaml with new expected scores

## Gold Standard Source

All gold-design.md and gold-prd.md files are direct copies from:
`/home/ercohen/go/src/github/eranco74/osac-workspace/enhancement-proposals/enhancements/`

The `gold_design_path` in annotations.yaml points to the original file for traceability.
