# 11 Roadmap 12 Months

## Purpose
Provide a realistic 12-month execution roadmap for independence, grounded in current repository architecture.

## Planning Model
Roadmap is organized in six two-month phases to balance delivery and risk.

## Phase 1 (Months 1-2): Architecture Freeze And Inventory Closure
Objective:
- lock boundaries and dependency inventory

Deliverables:
- approved ADR and architecture boundary docs
- tracked Debian dependency replacement backlog
- initial adapter contract draft

Dependencies:
- current docs and build scripts (`build/`, `config/`, `apps/`)

Risks:
- unclear boundaries causing scope churn

Parallelizable work:
- package boundary draft
- CI gate taxonomy draft

Exit criteria:
- dependency inventory linked to implementation tickets

## Phase 2 (Months 3-4): Package Foundations
Objective:
- introduce package-first scaffolding while preserving current output

Deliverables:
- package templates for first-party components
- CI package build artifacts (non-release)
- package ownership mapping for units, desktop files, policies

Dependencies:
- module boundaries from Phase 1

Risks:
- package split mismatch with runtime assumptions

Parallelizable work:
- adapter module skeleton
- release metadata schema draft

Exit criteria:
- at least core packages build in CI prototype job

## Phase 3 (Months 5-6): Image Pipeline Prototype
Objective:
- produce prototype package-driven images in parallel with current build

Deliverables:
- image definition schema and parser
- rootfs assembly prototype
- nightly VM boot smoke for prototype image

Dependencies:
- package build outputs from Phase 2

Risks:
- reproducibility and boot regressions

Parallelizable work:
- installer redesign prototyping
- channel/signing tooling prep

Exit criteria:
- package-driven prototype boots in CI nightly

## Phase 4 (Months 7-8): Installer Transition
Objective:
- migrate from preseed late-overlay path to NM-OS-controlled installer logic

Deliverables:
- installer module workflow for disk/encryption/user/profile
- post-install bootstrap without tar overlay extraction
- installer E2E test scenarios

Dependencies:
- image pipeline prototype

Risks:
- partition and encryption edge-case failures

Parallelizable work:
- recovery integration
- localization and UX polishing

Exit criteria:
- RC installer path works without Debian preseed injection

## Phase 5 (Months 9-10): Update, Signing, Recovery
Objective:
- implement release lifecycle trust and rollback basics

Deliverables:
- signed package metadata and release manifest
- channel workflows (nightly/beta/stable)
- recovery image/entry and diagnostics flow

Dependencies:
- package and installer transitions

Risks:
- key management operations and update rollback complexity

Parallelizable work:
- hardware matrix expansion
- support runbooks

Exit criteria:
- beta channel updates and recovery flow pass defined gates

## Phase 6 (Months 11-12): Release Hardening
Objective:
- prepare first independent stable release candidate

Deliverables:
- RC gate checklist automation
- official hardware support matrix and pass report
- migration guide from alpha installs

Dependencies:
- all previous phases

Risks:
- late regression concentration

Parallelizable work:
- documentation and contributor onboarding

Exit criteria:
- stable candidate passes QA/recovery/hardware/security gate set

## Top Cross-Phase Risks
- installer complexity underestimation
- package/repository signing operational gaps
- insufficient hardware validation bandwidth

## Fact / Inference / Assumption
- FACT: current repo has enough modularity and CI to start phased migration.
- INFERENCE: dual-path period (current build + future pipeline) is unavoidable for safety.
- ASSUMPTION: team can sustain parallel infrastructure and product work streams over 12 months.

