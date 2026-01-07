# Plan — Install miarecweb with UV

## Summary

The miarecweb package (version 2025.12.2.373+) has migrated from pip to UV, removing the `requirements.txt` file from package distribution. The current Ansible role uses pip and depends on `requirements.txt`, which breaks with newer miarecweb versions. This plan migrates the role from pip-based to UV-based package installation while maintaining backward compatibility with older setuptools-based packages.

The implementation replaces four pip-related tasks in `miarecweb.yml` (venv creation, pip upgrade, requirements.txt install, package install) with two UV commands (venv creation and editable install). It also replaces the mod_wsgi installation in `apache.yml` from Ansible's pip module to a UV shell command. The existing directory structure, variable interface, and idempotence behavior remain unchanged.

The work is divided into two phases: Phase 1 handles the core miarecweb installation in `miarecweb.yml`, and Phase 2 handles mod_wsgi installation in `apache.yml`. This separation allows independent testing and isolates any potential mod_wsgi build issues from the main package installation.

## 0. References

### 0.1 Specification (Always Read)
- [spec.md](spec.md) — Detailed specification with acceptance criteria. **Read before any implementation.**

### 0.2 Phase Plans (Read Relevant Phase)
- [plan_phase_1.md](plan_phase_1.md) — Phase 1: Replace pip with UV in miarecweb.yml
- [plan_phase_2.md](plan_phase_2.md) — Phase 2: Replace pip with UV in apache.yml

### 0.3 Research (Read to Understand Codebase)
- [research.md](research.md) — Codebase exploration, component mapping, existing patterns.

### 0.4 Source Document (Read if Requested)
- [idea.md](idea.md) — Original problem analysis and solution hypothesis.

## 1. Software Design Document (SDD)

### 1.1 Goals & Constraints

**Goals:**
- Replace pip-based virtual environment creation and package installation with UV
- Maintain backward compatibility with both setuptools-based and UV-based miarecweb packages
- Preserve the existing directory structure (`/opt/miarecweb/releases/VERSION/pyenv`)
- Maintain idempotence of the role
- Support Python version specification via existing `python_version` variable

**Constraints:**
1. **UV availability**: UV must be installed before `miarecweb.yml` runs. The existing `install_uv.yml` guarantees this in `main.yml` task order.
2. **No Python downloads**: Use `--no-python-downloads` flag to prevent UV from downloading Python. The role relies on system Python validated by `preflight.yml`.
3. **File permissions**: All commands must use `umask 0022 &&` prefix for world-readable files (Apache/mod_wsgi requirement).
4. **Idempotence**: Use `creates:` argument to skip tasks when target files exist.

**Out of scope:**
- UV installation (already done in PR #14)
- Python installation/detection (already handled in `preflight.yml`)
- Changes to role interface (existing variables unchanged)

### 1.2 Proposed Architecture (High-level)

**Current flow (pip-based):**
```
miarecweb.yml:
  1. Download tarball → extract to /opt/miarecweb/releases/X.Y.Z.N/app/
  2. python -m venv → create /opt/miarecweb/releases/X.Y.Z.N/pyenv/
  3. pip install --upgrade pip setuptools
  4. pip install -r requirements.txt
  5. pip install -e .

apache.yml:
  6. pip install mod_wsgi==VERSION
```

**Proposed flow (UV-based):**
```
miarecweb.yml:
  1. Download tarball → extract (unchanged)
  2. uv venv --python VERSION --no-python-downloads PATH
  3. (removed - not needed with UV)
  4. (removed - merged into step 5)
  5. uv pip install -e . --python PATH

apache.yml:
  6. uv pip install mod_wsgi==VERSION --python PATH
```

**Key changes:**
- Steps 3 and 4 are eliminated entirely
- Step 2: `python -m venv` → `uv venv`
- Step 5: `pip install -e .` → `uv pip install -e .`
- Step 6: Ansible `pip` module → shell command with `uv pip install`

### 1.3 Data Model & Types

**Variables used (existing, no changes):**
```yaml
uv_install_dir: /usr/local/bin          # UV binary location
python_version_base: "3.12"              # Set by preflight.yml
miarecweb_version: "2025.12.2.373"       # User-provided
mod_wsgi_version: "5.0.0"                # Default from defaults/main.yml
ansible_facts['deploy_helper']['new_release_path']  # e.g., /opt/miarecweb/releases/X.Y.Z.N
```

### 1.4 Module / File-level Design

**tasks/miarecweb.yml:**

| Lines | Current Task | Action |
|-------|-------------|--------|
| 68-72 | Create venv with `python -m venv` | **Replace** with `uv venv` command |
| 74-79 | Upgrade pip/setuptools | **Remove** entirely |
| 81-89 | Install requirements.txt | **Remove** entirely |
| 91-96 | Install miarecweb with pip | **Replace** with `uv pip install -e .` |

**tasks/apache.yml:**

| Lines | Current Task | Action |
|-------|-------------|--------|
| 51-57 | Install mod_wsgi with Ansible pip module | **Replace** with `uv pip install` shell command |

**No changes to:**
- `tasks/preflight.yml` - Python detection unchanged
- `tasks/install_uv.yml` - Already implemented
- `tasks/main.yml` - Task order unchanged
- `defaults/main.yml` - Variables unchanged

### 1.5 Interfaces & Contracts

**UV Commands (exact syntax):**

1. **Create virtual environment:**
```bash
umask 0022 && {{ uv_install_dir }}/uv venv \
  --python {{ python_version_base }} \
  --no-python-downloads \
  {{ ansible_facts['deploy_helper']['new_release_path'] }}/pyenv
```

2. **Install miarecweb package:**
```bash
umask 0022 && {{ uv_install_dir }}/uv pip install -e . \
  --python {{ ansible_facts['deploy_helper']['new_release_path'] }}/pyenv/bin/python
```

3. **Install mod_wsgi:**
```bash
umask 0022 && {{ uv_install_dir }}/uv pip install mod_wsgi=={{ mod_wsgi_version }} \
  --python {{ ansible_facts['deploy_helper']['new_release_path'] }}/pyenv/bin/python
```

### 1.6 Key Algorithms

No complex algorithms involved. The implementation is straightforward command replacement with idempotence checks via `creates:` argument.

### 1.7 Testing Architecture

**Test strategy:**
- Use existing Molecule test infrastructure (no new test files needed)
- Run `molecule test` which includes converge + idempotence check + verify
- Test matrix: 2 miarecweb versions × 4+ distros

**Test scenarios:**

| miarecweb version | Package type | Purpose |
|-------------------|--------------|---------|
| 2025.12.2.15 | setuptools-based | Backward compatibility |
| 2025.12.2.373 | UV-based | New format support |

**Distros to test:**
- ubuntu2204, ubuntu2404, rockylinux8, rockylinux9

**Verification points (existing tests cover these):**
- `test_directories()` - pyenv directory exists
- `test_script()` - Python venv works (runs create_root_user)
- `test_health_endpoint()` - Application responds
- Idempotence check - Second run makes no changes

**Linting:**
- `uv run ansible-lint` must pass

### 1.8 Edge Cases

| Edge Case | Handling |
|-----------|----------|
| **UV not installed** | Role will fail at `uv venv` command with clear error. User must run with `-t uv` tag first. |
| **Python version not found** | `--no-python-downloads` causes UV to fail with clear error. Existing `preflight.yml` validation should catch this earlier. |
| **Restrictive umask (027)** | All shell commands use `umask 0022 &&` prefix to ensure world-readable files. |
| **Old miarecweb (setuptools)** | `uv pip install -e .` handles both `setup.py` and `pyproject.toml` formats automatically. |
| **Partial installation** | `creates:` argument ensures idempotence. If venv exists but package not installed, only package install runs. |
| **mod_wsgi build failure** | If `uv pip install mod_wsgi` fails, spec says add fallback only if needed. Try direct approach first. |

### 1.9 Observability & Ops

No changes needed. Ansible task output naturally shows UV commands and their results.

## 2. Phase Breakdown

### Phase 1. Replace pip with UV in miarecweb.yml (pending)

**Goal:** Migrate venv creation and miarecweb package installation from pip to UV.

**Acceptance criteria:**
- Venv created at `{{ release_path }}/pyenv` using UV
- miarecweb package installed using UV
- No pip upgrade or requirements.txt tasks remain
- Role is idempotent
- `uv run ansible-lint` passes

**Plan:** [plan_phase_1.md](plan_phase_1.md)

### Phase 2. Replace pip with UV in apache.yml (pending)

**Goal:** Migrate mod_wsgi installation from Ansible pip module to UV.

**Acceptance criteria:**
- mod_wsgi installed using UV
- Apache starts successfully with mod_wsgi
- Role is idempotent
- `uv run ansible-lint` passes

**Plan:** [plan_phase_2.md](plan_phase_2.md)

## 3. Living Sections (Mandatory)

> **Instructions for maintainers:**
>
> This plan is a living document. As you make key design decisions, update the plan to record both the decision and the thinking behind it. Record all decisions in the `Decision Log` section.
>
> Maintain the `Progress` section in this plan and in the corresponding phase document. Mark tasks as `[ ]` not started, `[~]` in progress, or `[x]` done.
>
> When you discover optimizer behavior, performance tradeoffs, unexpected bugs, or inverse/unapply semantics that shaped your approach, capture those observations in the `Surprises & Discoveries` section with short evidence snippets (test output is ideal).
>
> If you change course mid-implementation, document why in the `Decision Log` and reflect the implications in `Progress`. Plans are guides for the next contributor as much as checklists for you.
>
> At completion of a major task or the full plan, write an `Outcomes & Retrospective` entry summarizing what was achieved, what remains, and lessons learned.
>
> **This document must describe not just the what but the why for almost everything.**

### 3.1 Progress

- [ ] Phase 1: Replace pip with UV in miarecweb.yml
  - [ ] Task 1.1: Replace venv creation task
  - [ ] Task 1.2: Remove pip upgrade task
  - [ ] Task 1.3: Remove requirements.txt task
  - [ ] Task 1.4: Replace miarecweb install task
- [ ] Phase 2: Replace pip with UV in apache.yml
  - [ ] Task 2.1: Replace mod_wsgi install task

### 3.2 Decision Log

- **Decision:** Use 2-phase approach (miarecweb.yml first, apache.yml second)
  - Date: 2026-01-07
  - Rationale: Isolates core package installation from mod_wsgi, allowing independent testing and easier debugging if mod_wsgi has build issues.

- **Decision:** Remove PATH environment variable for psycopg
  - Date: 2026-01-07
  - Rationale: New miarecweb packages no longer require pg_config for psycopg build.

### 3.3 Surprises & Discoveries

(To be filled during implementation)

### 3.4 Outcomes & Retrospective

(To be filled after completion)
