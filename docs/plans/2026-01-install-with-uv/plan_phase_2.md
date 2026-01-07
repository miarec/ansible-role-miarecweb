# Phase 2 — Replace pip with UV in apache.yml

## Goal

Migrate mod_wsgi installation from Ansible pip module to UV in `tasks/apache.yml`.

## Scope

- File: `tasks/apache.yml`
- Lines: 51-57 (1 task to modify)

## Tasks

- [x] **Task 2.1: Replace mod_wsgi install task (lines 51-57)** (completed 2026-01-07)
  - Current: Ansible `pip` module with `executable:` parameter
  - New: Shell command with `uv pip install`
  - Keep version pinning
  - Add `creates:` argument for idempotence
  - Command:
    ```yaml
    - name: Install mod_wsgi python package
      ansible.builtin.shell:
        cmd: >-
          umask 0022 &&
          {{ uv_install_dir }}/uv pip install mod_wsgi=={{ mod_wsgi_version }}
          --python {{ ansible_facts['deploy_helper']['new_release_path'] }}/pyenv/bin/python
        creates: "{{ ansible_facts['deploy_helper']['new_release_path'] }}/pyenv/lib/python{{ python_version_base }}/site-packages/mod_wsgi"
    ```

## Acceptance Criteria

- [ ] mod_wsgi installed using UV
- [ ] Apache starts successfully with mod_wsgi
- [ ] Role is idempotent (second run shows no changes)
- [ ] `uv run ansible-lint` passes

## Tests (Must be implemented in this phase)

No new test files needed. Existing Molecule tests cover:

- `test_service()` - Verifies Apache is running
- `test_socket()` - Verifies ports 80/443 are listening
- `test_health_endpoint()` - Verifies application responds via Apache/mod_wsgi
- Idempotence check - Built into `molecule test`

## Edge Cases to Address

| Edge Case | How Addressed |
|-----------|---------------|
| mod_wsgi build failure | If `uv pip install mod_wsgi` fails during testing, add fallback (install pip into venv, then use pip). Spec defers this decision to implementation. |
| Restrictive umask | `umask 0022 &&` prefix ensures world-readable files |
| Version pinning | Use `mod_wsgi=={{ mod_wsgi_version }}` syntax |

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

# Test with both miarecweb versions
MOLECULE_MIARECWEB_VERSION=2025.12.2.15 uv run molecule test
MOLECULE_MIARECWEB_VERSION=2025.12.2.373 uv run molecule test
```
