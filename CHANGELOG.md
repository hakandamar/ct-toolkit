# Changelog

All notable changes to the **Computational Theseus Toolkit (CT Toolkit)** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

*(Note: This project uses `python-semantic-release` for automated versioning and changelog generation. Future automated releases will append updates here.)*

## [0.3.6] - 2026-03-21

### Added
- **Core Context Compression Guard**: Integrated `ContextCompressionGuard` into the core toolkit layer.
- **Passive Compression Detection**: Universal, provider-agnostic detection of "silent" context compression (e.g., OpenAI compaction, Anthropic beta summarization) using message history shrinkage analysis.
- **Passive Detection Heuristic**: Automatic drift analysis triggers when context history shrinks significantly (>30% drop).
- **Middleware Propagations**: Enhanced `crewai`, `langchain`, and `deepagents` middlewares to inherit compression settings from the parent `WrapperConfig`.

### Changed
- **Unified Configuration**: Moved `compression_threshold` and `compression_passive_detection` into the standard `WrapperConfig`.
- **Exposed Property**: `TheseusChatModel` (LangChain) now exposes `compression_guard` for manual audits.

## [0.3.5] - 2026-03-19

### Added
- **Standalone Auditor CLI**: Introduced `ct-toolkit` command-line interface for independent L3 ICM audits.
- **ASCII Art Banner**: Added "THESEUS GUARD" branding to CLI startup.
- **Auditor Commands**: Added `audit`, `list-kernels`, and `list-templates` to the CLI.
- **CLI Documentation**: Added comprehensive guides and examples for CLI usage on the website.

### Fixed
- Improved error handling in `ICMRunner` for empty probe batteries and failed LLM connections.
- Resolved package versioning inconsistency in `__init__.py`.

## [0.3.4] - 2026-03-19

### Added
- Redesigned documentation website to align with Google ADK Docs 2.0 style.
- Enhanced homepage with interactive card grid and optimized hero section.
- Integrated SVG logo and favicon for professional branding.
- Expanded technical documentation for Identity Continuity and Divergence Engine.

### Fixed
- Improved Dark Mode support with theme-aware CSS overrides for grid cards.
- Fixed Markdown parsing issues in website homepage layout.

### Added (Previous Unreleased)
- Comprehensive API Reference documentation focusing on high Developer Experience.
- Repository `SECURITY.md`, `CHANGELOG.md`, and updated `CONTRIBUTING.md`.

## [0.3.3] - 2026-03-19

### Changed
- Core API restructuring and improvements towards stability and plasticity scheduling.
- Compatibility layer enhancements.

## [0.2.5] - 2026-03-16

### Security
- Latest security hardening changes implemented to prevent configuration tampering.

## [0.2.4] - 2026-03-15

### Added
- Auto-Correction loop mechanism allowing autonomous retry of agentic failures when Identity Drift is detected by L2 Judge.
- New endpoints and domain probes for real-world scenarios.

### Fixed
- Fixed packaging configuration regarding identity templates `FileNotFoundError`.
- Addressed PyPI version discrepancy mapping issues.

## [0.2.0] - Initial Public Structuring

### Added
- Core `TheseusWrapper` and `ConstitutionalKernel` logic.
- Divergence Engine with multi-tiered (L1/L2/L3) mechanisms.
- Provenance Vault using SQLite and HMAC hash chaining.
