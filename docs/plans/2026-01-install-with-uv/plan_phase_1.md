# Phase 1 — Replace pip with UV in miarecweb.yml

## Goal

Migrate virtual environment creation and miarecweb package installation from pip to UV in `tasks/miarecweb.yml`.

## Scope

- File: `tasks/miarecweb.yml`
- Lines: 68-96 (4 tasks to modify/remove)

## Tasks

- [x] **Task 1.1: Replace venv creation task (lines 68-72)** (completed 2026-01-07)
  - Current: `python -m venv PATH`
  - New: `uv venv --python VERSION --no-python-downloads PATH`
  - Command:
    ```yaml
    - name: Create python virtual environment
      ansible.builtin.shell:
        cmd: >-
          umask 0022 &&
          {{ uv_install_dir }}/uv venv
          --python {{ python_version_base }}
          --no-python-downloads
          {{ ansible_facts['deploy_helper']['new_release_path'] }}/pyenv
        creates: "{{ ansible_facts['deploy_helper']['new_release_path'] }}/pyenv"
    ```

- [x] **Task 1.2: Remove pip upgrade task (lines 74-79)** (completed 2026-01-07)
  - Delete "Upgrade PIP and setuptools" task entirely
  - Rationale: UV handles package management internally, no need to upgrade pip/setuptools

- [x] **Task 1.3: Remove requirements.txt task (lines 81-89)** (completed 2026-01-07)
  - Delete "Install dependencies (requirements.txt)" task entirely
  - Rationale: `uv pip install -e .` reads dependencies from pyproject.toml/setup.py

- [x] **Task 1.4: Replace miarecweb install task (lines 91-96)** (completed 2026-01-07)
  - Current: `pip install -e .`
  - New: `uv pip install -e . --python PATH`
  - Remove `environment: PATH` block (not needed for psycopg)
  - Command:
    ```yaml
    - name: Install MiaRecWeb
      ansible.builtin.shell:
        cmd: >-
          umask 0022 &&
          {{ uv_install_dir }}/uv pip install -e .
          --python {{ ansible_facts['deploy_helper']['new_release_path'] }}/pyenv/bin/python
        chdir: "{{ ansible_facts['deploy_helper']['new_release_path'] }}/app"
        creates: "{{ ansible_facts['deploy_helper']['new_release_path'] }}/pyenv/lib/python{{ python_version_base }}/site-packages/miarecweb-{{ miarecweb_version }}.dist-info"
    ```

## Acceptance Criteria

- [ ] Venv created at `{{ release_path }}/pyenv` using UV
- [ ] miarecweb package installed using UV
- [ ] No pip upgrade or requirements.txt tasks remain in miarecweb.yml
- [ ] Role is idempotent (second run shows no changes)
- [ ] `uv run ansible-lint` passes

## Tests (Must be implemented in this phase)

No new test files needed. Existing Molecule tests cover:

- `test_directories()` - Verifies pyenv directory exists
- `test_script()` - Runs create_root_user script (validates Python venv works)
- `test_health_endpoint()` - Verifies application responds
- Idempotence check - Built into `molecule test`

Test with both miarecweb versions:
- Setuptools-based: `MOLECULE_MIARECWEB_VERSION=2025.12.2.15`
- UV-based: `MOLECULE_MIARECWEB_VERSION=2025.12.2.373`

## Edge Cases to Address

| Edge Case | How Addressed |
|-----------|---------------|
| UV not installed | Command fails with clear error; user must run with `-t uv` first |
| Python version not found | `--no-python-downloads` causes clear failure; preflight.yml validates earlier |
| Restrictive umask | `umask 0022 &&` prefix ensures world-readable files |
| Old miarecweb (setuptools) | `uv pip install -e .` handles both setup.py and pyproject.toml |

## Verification Steps

```bash
# Lint check first
uv run ansible-lint

# Test on ubuntu2404
MOLECULE_DISTRO=ubuntu2404 uv run molecule test

# Test idempotence explicitly
MOLECULE_DISTRO=ubuntu2404 uv run molecule converge
MOLECULE_DISTRO=ubuntu2404 uv run molecule idempotence

# Test on other distros
MOLECULE_DISTRO=ubuntu2204 uv run molecule test
MOLECULE_DISTRO=rockylinux8 uv run molecule test
MOLECULE_DISTRO=rockylinux9 uv run molecule test

# Test with old miarecweb version (backward compatibility)
MOLECULE_MIARECWEB_VERSION=2025.12.2.15 uv run molecule test
```
