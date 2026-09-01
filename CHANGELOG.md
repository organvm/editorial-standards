# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Reader-mode repository documentation standard with A–F repository classes
- Normative project-record contract linked to the canonical schema package
- README v2, five audience-edition, and evidence-record templates
- Seven-dimension repository documentation audit rubric
- LOGOS Sprint: Initial repository creation
- Voice specification for ORGAN-V discourse layer
- Five canonical essay category definitions
- 12-field frontmatter schema with types and constraints
- 100-point quality rubric across five scoring dimensions
- Naming conventions for posts, series, and tag taxonomy
- Review process with pre-publish checklist and human synthesis gate
- ADR-001: Initial architecture decisions
- ADR-002: Quality rubric design rationale

### Fixed
- Separated structured claim posture from assertion verification state and
  removed unconditional cross-route links from audience templates
- Scoped CI template checks by contract and pinned external workflow actions to
  immutable revisions
- Reconciled all README frontmatter, category, naming, tag, and review guidance
  with the authoritative 12-field schema, with CI regression coverage
- Expanded `related_repos` validation to canonical consolidated and legacy
  ORGANVM `owner/repository` slugs
- Updated repository, pipeline, public-process, and contributing links after consolidation

## [0.1.0] - 2026-02-17

### Added
- Initial repository structure
- README.md with full editorial governance documentation
- seed.yaml automation contract
- CI workflow (ci-minimal template)
- MIT License
- CHANGELOG.md

[Unreleased]: https://github.com/organvm/editorial-standards/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/organvm/editorial-standards/releases/tag/v0.1.0
