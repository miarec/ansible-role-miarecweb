# Pull Request Description

## Summary

Migrate from pip/requirements.txt to uv for dependency management, drop legacy OS support (CentOS 7, RHEL 7/8, Rocky 8, Ubuntu 20.04), switch Python installation from source compilation to system packages, and improve Python version handling with auto-detection.

---

## Purpose

- **Simplify dependency management**: uv provides faster, more reliable Python package management with reproducible lockfiles
- **Reduce test matrix complexity**: Older OS versions (CentOS 7, RHEL 7/8) reached end-of-life and required complex workarounds for Python compilation
- **Faster CI**: Using system Python packages eliminates 5-10 minute compilation step per test run
- **Modern tooling alignment**: Aligns with current best practices for Python project management
- **Flexible Python version handling**: Auto-detect Python version from system or allow explicit specification

---

## Testing

* [x] Added/updated tests
* [x] Ran `uv run ansible-lint`
* [x] Molecule tests pass on Ubuntu 24.04 and Rocky Linux 9
* Notes: Linting passes with 0 failures. Molecule tests require Docker environment to run locally.

---

## Related Issues

N/A

---

## Changes

### uv Migration
* Added `pyproject.toml` and `uv.lock` for dependency management
* Removed `test-requirements.txt`
* CI workflow now uses `astral-sh/setup-uv@v4` instead of pip

### Python Version Handling
* **Auto-detection**: Python version is now auto-detected from system if `python_version` is not specified
* **Flexible specification**: `python_version` supports formats like "3.12", "3.12.1", or "3" (major only)
* **Version validation**: Detected version is validated against `python_minimum_version` (3.10) and `python_maximum_version` (3.12)
* **OS-specific package handling**:
  - Debian: Installs python3-packaging, python3-pip, python3-venv via apt (PEP 668 compliance)
  - RedHat: Installs packaging via pip

### Idempotence Fixes
* Changed MiaRecWeb install check from `.egg-link` to `.dist-info` directory (modern pip compatibility)
* Moved Python version detection to preflight.yml to ensure consistent state

### System Python
* Molecule now installs Python from OS packages instead of compiling from source
* `python_install_dir` defaults to `/usr` for packages, `/usr/local` for source builds
* Uses system PostgreSQL packages instead of pgdg repo in molecule tests

### Dropped OS Support
* Removed from test matrix: ubuntu2004, centos7, rockylinux8, rhel7, rhel8
* Updated meta/main.yml to reflect supported platforms: Ubuntu 22.04/24.04 (jammy/noble), EL 9

### Molecule Test Improvements
* Added Redis installation to prepare stage
* Moved task files into `molecule/default/tasks/` subdirectory
* Added `MOLECULE_PYTHON_VERSION` environment variable support
* Simplified converge.yml by removing redundant variables
* Added individual stage documentation to README and CLAUDE.md

### Code Modernization
* Replaced legacy `ansible_os_family` with `ansible_facts['os_family']` throughout
* Replaced `deploy_helper` with `ansible_facts['deploy_helper']`

### Documentation
* Added CLAUDE.md with development instructions and architecture overview
* Added AGENTS.md
* Updated README with uv testing instructions and individual molecule stage examples

---

## Notes for Reviewers

* The `python_install_from_source` variable defaults to `false`. Set to `true` if using compiled Python.
* Supported OS matrix is now: Ubuntu 22.04/24.04, Rocky Linux 9, RHEL 9
* The `MOLECULE_MIARECWEB_PYTHON_VERSION` environment variable is no longer needed (Python version auto-detected from system)
* `python_version` can be left empty for auto-detection or set explicitly (e.g., "3.12")

---

## Docs

* [x] Updated relevant documentation
