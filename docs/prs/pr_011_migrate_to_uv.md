# Pull Request Description Template

## Summary

Migrate from pip/requirements.txt to uv for dependency management, drop legacy OS support (CentOS 7, RHEL 7/8, Rocky 8, Ubuntu 20.04), and switch Python installation from source compilation to system packages.

---

## Purpose

- **Simplify dependency management**: uv provides faster, more reliable Python package management with reproducible lockfiles
- **Reduce test matrix complexity**: Older OS versions (CentOS 7, RHEL 7/8) reached end-of-life and required complex workarounds for Python compilation
- **Faster CI**: Using system Python packages eliminates 5-10 minute compilation step per test run
- **Modern tooling alignment**: Aligns with current best practices for Python project management

---

## Testing

How did you verify it works?

* [x] Added/updated tests
* [x] Ran `uv run ansible-lint`
* Notes: Linting passes with 0 failures. Molecule tests require Docker environment to run locally.

---

## Related Issues

N/A

---

## Changes

Brief list of main changes:

* **uv migration**: Added `pyproject.toml` and `uv.lock`, removed `test-requirements.txt`
* **CI workflow**: Replaced pip installation with `astral-sh/setup-uv@v4`, simplified test matrix
* **System Python**: Molecule now installs Python from OS packages instead of compiling from source
* **Dropped OS support**: Removed ubuntu2004, centos7, rockylinux8, rhel7, rhel8 from test matrix
* **Added Redis**: Molecule prepare now installs Redis for testing
* **ansible_facts syntax**: Replaced legacy `ansible_os_family` with `ansible_facts['os_family']` throughout
* **Molecule refactoring**: Moved task files into `molecule/default/tasks/` subdirectory
* **Documentation**: Added CLAUDE.md, AGENTS.md, updated README with uv testing instructions
* **Default variables**: `python_install_dir` is now dynamic (`/usr` for packages, `/usr/local` for source)

---

## Notes for Reviewers

* The `python_install_from_source` variable defaults to `false`. Set to `true` if using compiled Python.
* Supported OS matrix is now: Ubuntu 22.04/24.04, Rocky Linux 9, RHEL 9
* The `MOLECULE_MIARECWEB_PYTHON_VERSION` environment variable is no longer needed (Python version auto-detected from system)

---

## Docs

* [x] Updated relevant documentation
