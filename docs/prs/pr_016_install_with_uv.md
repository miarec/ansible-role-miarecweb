# Pull Request Description Template

## Summary

Replace pip with UV for Python package installation in the miarecweb Ansible role.

This PR migrates virtual environment creation and package installation from pip to UV, enabling support for new UV-based miarecweb packages (2025.12.2.373+) while maintaining backward compatibility with older setuptools-based packages.

---

## Purpose

The miarecweb package has migrated from pip to UV starting with version 2025.12.2.373. This change:
- Removes `requirements.txt` from the package distribution
- Uses `pyproject.toml` with UV for dependency management

The current Ansible role depends on `requirements.txt` for installing dependencies, which breaks with newer miarecweb versions. This PR updates the role to use UV for all Python package operations.

---

## Testing

How did you verify it works?

* [x] Ran `uv run ansible-lint` - passed
* [x] Molecule tests pass on ubuntu2404 with old version (2025.12.2.15)
* [x] Molecule tests pass on ubuntu2404 with new version (2025.12.2.373)
* [x] Molecule tests pass on rockylinux8 with both versions
* [x] Molecule tests pass on rockylinux9 with both versions
* [x] TLS scenario tests pass on ubuntu2404 and rockylinux9
* [x] Idempotence verified (no changes on second run)

Notes:
- All tests run locally passed (10 test combinations)
- CI will additionally test ubuntu2204, rhel8, rhel9

---

## Related Issues

Depends on PR #14 (Install UV binary) which is already merged.

---

## Changes

Brief list of main changes:

* **tasks/miarecweb.yml**: Replace `python -m venv` with `uv venv --python VERSION --no-python-downloads`
* **tasks/miarecweb.yml**: Remove "Upgrade PIP and setuptools" task (UV handles internally)
* **tasks/miarecweb.yml**: Remove "Install dependencies (requirements.txt)" task (UV reads from pyproject.toml)
* **tasks/miarecweb.yml**: Replace `pip install -e .` with `uv pip install -e . --python PATH`
* **tasks/apache.yml**: Replace Ansible `pip` module with `uv pip install mod_wsgi` shell command
* **docs/plans/2026-01-install-with-uv/**: Add planning documents (idea, spec, research, plan, phase plans)

---

## Notes for Reviewers

**Key implementation decisions:**

1. **UV commands use full path**: `{{ uv_install_dir }}/uv` ensures the correct UV binary is used regardless of PATH.

2. **`--no-python-downloads` flag**: Prevents UV from downloading Python. The role relies on system Python validated by `preflight.yml`.

3. **`umask 0022 &&` prefix**: All shell commands use this prefix to ensure world-readable files (required by Apache/mod_wsgi).

4. **Idempotence via `creates:`**: Both venv creation and package installation use `creates:` argument to skip tasks when target files exist.

5. **Removed PATH for psycopg**: The `environment: PATH` block that added `pg_config` is removed. New miarecweb packages no longer require pg_config for psycopg build.

**Backward compatibility:**
- UV's `uv pip install -e .` handles both `setup.py` (old) and `pyproject.toml` (new) package formats automatically
- Tested with both setuptools-based (2025.12.2.15) and UV-based (2025.12.2.373) miarecweb packages

---

## Docs

* [x] Updated `docs/plans/2026-01-install-with-uv/plan.md` with test results and outcomes
