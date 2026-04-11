# 12 First Sprint

## Purpose
Define the first implementation sprint that can start immediately in this repository with low-risk, high-leverage work.

## Sprint Goal
Create the minimum operational foundation for independence work without breaking current build/install/runtime behavior.

## Scope
5-10 concrete tasks with file-level targets and explicit acceptance criteria.

## Task List
1. Add adapter contract documentation and capability map
- Files:
  - `docs/independence/02-modular-architecture.md` (extend)
  - new `docs/independence/templates/platform-adapter-contract.md`
- Done when:
  - required adapter capabilities are listed and mapped to current scripts

2. Add package definition template set
- Files:
  - `docs/independence/templates/package-template.yaml`
  - `docs/independence/templates/package-set-template.yaml`
- Done when:
  - each proposed NM-OS package can be represented by template fields

3. Add image definition template and sample profiles
- Files:
  - `docs/independence/templates/image-definition-template.yaml`
  - `docs/independence/templates/sample-desktop-image.yaml`
  - `docs/independence/templates/sample-installer-image.yaml`
- Done when:
  - base/desktop/installer/recovery profiles can be expressed in one schema

4. Add release metadata and signing manifest templates
- Files:
  - `docs/independence/templates/release-manifest-template.json`
  - `docs/independence/templates/signing-policy-template.md`
- Done when:
  - nightly/beta/stable metadata fields are documented and exampled

5. Add QA gate checklist artifact for RC
- Files:
  - `docs/independence/templates/rc-gate-checklist.md`
  - `docs/independence/10-qa-release-gates.md` (cross-link)
- Done when:
  - checklist is directly usable for manual RC decision

6. Add dependency replacement tracker skeleton
- Files:
  - `docs/independence/templates/dependency-replacement-tracker.md`
  - `docs/independence/01-debian-dependency-inventory.md` (cross-link)
- Done when:
  - every high-risk dependency has owner/status placeholders

7. Add minimal roadmap execution board document
- Files:
  - `docs/independence/templates/phase-board-template.md`
  - `docs/independence/11-roadmap-12-months.md` (cross-link)
- Done when:
  - each roadmap phase has owner/ETA/status placeholder rows

8. Add sprint CI check for independence docs integrity (links/files exist)
- Files:
  - `tests/smoke/verify-structure.sh` (optional low-risk extension)
  - `tests/smoke/verify-independence-docs.sh` (new low-risk script)
  - `.github/workflows/smoke.yml` (optional include)
- Done when:
  - docs program cannot regress silently

Current status:
- implemented in this repository iteration.

## Suggested Execution Order
1. templates for package/image/release
2. tracker/checklist artifacts
3. optional smoke check for docs integrity

## Risks
- Over-engineering templates before implementation owners are assigned.
- CI noise if docs checks are too strict too early.

## Exit Criteria
- Sprint outputs exist in repo and are referenced from program docs.
- No regression in current smoke/build pipeline.

## Fact / Inference / Assumption
- FACT: current repo supports low-risk docs and smoke additions without runtime changes.
- INFERENCE: template-led sprint reduces ambiguity before infrastructure coding starts.
- ASSUMPTION: team wants immediate implementation scaffolding, not only analysis artifacts.
