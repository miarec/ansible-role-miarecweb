# Codebase Research for UV Migration

## 1. Research Scope

- **Spec version/date referenced**: `docs/plans/2026-01-install-with-uv/spec.md`
- **Areas searched**:
  - Task files: `miarecweb.yml`, `apache.yml`, `preflight.yml`, `install_uv.yml`, `dependencies.yml`, `main.yml`
  - Variable definitions: `defaults/main.yml`, `vars/Debian.yml`, `vars/RedHat.yml`
  - Test infrastructure: `molecule/` scenarios, `.github/workflows/ci.yml`
  - Role dev configuration: `pyproject.toml` (Ansible/molecule dependencies)

## 2. Repo Orientation

### How to run / build / test (as discovered)

```bash
# Linting
uv run ansible-lint

# Full molecule test (default distro: ubuntu2404)
uv run molecule test

# Test with specific distro and miarecweb version
MOLECULE_DISTRO=ubuntu2204 MOLECULE_MIARECWEB_VERSION=2025.12.2.373 uv run molecule test

# Individual molecule stages for debugging
MOLECULE_DISTRO=ubuntu2404 uv run molecule create
MOLECULE_DISTRO=ubuntu2404 uv run molecule prepare
MOLECULE_DISTRO=ubuntu2404 uv run molecule converge
MOLECULE_DISTRO=ubuntu2404 uv run molecule verify
MOLECULE_DISTRO=ubuntu2404 uv run molecule idempotence
MOLECULE_DISTRO=ubuntu2404 uv run molecule destroy
```

### Key directories

| Directory | Purpose |
|-----------|---------|
| `tasks/` | Ansible task files (main execution logic) |
| `defaults/` | Default variable definitions |
| `vars/` | OS-specific variable overrides (Debian.yml, RedHat.yml) |
| `templates/` | Jinja2 templates for config files |
| `handlers/` | Service notification handlers |
| `molecule/` | Test scenarios (default, tls, uv, uv_upgrade) |
| `.github/workflows/` | CI pipeline definition |

## 3. Relevant Components (Map)

### 3.1 tasks/miarecweb.yml (Target for modification)

**Path**: `tasks/miarecweb.yml`

**Responsibilities**: Download miarecweb tarball, create Python virtual environment, install dependencies and miarecweb package, configure production.ini

**Key sections for UV migration**:

| Lines | Current Implementation | Notes |
|-------|----------------------|-------|
| 68-72 | Create venv: `python -m venv` | Replace with `uv venv --python VERSION --no-python-downloads PATH` |
| 74-79 | Upgrade pip/setuptools via `pip install --upgrade pip setuptools` | Remove (UV handles this internally) |
| 81-89 | Install requirements.txt via Ansible `pip` module | Remove (merged into editable install) |
| 91-96 | Install miarecweb via `pip install -e .` | Replace with `uv pip install -e . --python PATH` |

**Current venv creation** (lines 68-72):
```yaml
- name: Create python virtual environment
  shell:
    cmd: "umask 0022 && {{ python_install_dir }}/bin/python{{ python_version_base }} -m venv {{ ansible_facts['deploy_helper']['new_release_path'] }}/pyenv"
    creates: "{{ ansible_facts['deploy_helper']['new_release_path'] }}/pyenv"
  register: create_pyenv
```

**Current pip upgrade** (lines 74-79):
```yaml
- name: Upgrade PIP and setuptools    # noqa: no-handler
  shell:
    cmd: "umask 0022 && {{ ansible_facts['deploy_helper']['new_release_path'] }}/pyenv/bin/python -m pip install --upgrade pip setuptools"
    chdir: "{{ ansible_facts['deploy_helper']['new_release_path'] }}/app"
  changed_when: true
  when: create_pyenv.changed
```

**Current requirements.txt installation** (lines 81-89):
```yaml
- name: Install dependencies (requirements.txt)
  pip:
    requirements: requirements.txt
    executable: "{{ ansible_facts['deploy_helper']['new_release_path'] }}/pyenv/bin/pip"
    chdir: "{{ ansible_facts['deploy_helper']['new_release_path'] }}/app"
    umask: "0022"
  environment:
    PATH: "{{ postgresql_bin_directory }}:{{ ansible_env.PATH }}"
```

**Current miarecweb installation** (lines 91-96):
```yaml
- name: Install MiaRecWeb
  shell:
    cmd: "umask 0022 && {{ ansible_facts['deploy_helper']['new_release_path'] }}/pyenv/bin/pip install -e ."
    chdir: "{{ ansible_facts['deploy_helper']['new_release_path'] }}/app"
    creates: "{{ ansible_facts['deploy_helper']['new_release_path'] }}/pyenv/lib/python{{ python_version_base }}/site-packages/miarecweb-{{ miarecweb_version }}.dist-info"
```

**Inputs**:
- `ansible_facts['deploy_helper']['new_release_path']` - e.g., `/opt/miarecweb/releases/2025.12.2.373`
- `python_install_dir` - `/usr` or `/usr/local`
- `python_version_base` - e.g., `3.12`
- `postgresql_bin_directory` - needed for `pg_config` during psycopg2 build

**Outputs**:
- Virtual environment at `{{ release_path }}/pyenv/`
- Installed miarecweb package (editable mode)
- `.dist-info` directory in site-packages (used for idempotence check)

### 3.2 tasks/apache.yml (Target for modification)

**Path**: `tasks/apache.yml`

**Key section for UV migration**:

| Lines | Current Implementation | Notes |
|-------|----------------------|-------|
| 51-57 | Install mod_wsgi via Ansible `pip` module | Replace with `uv pip install mod_wsgi --python PATH` |

**Current mod_wsgi installation** (lines 51-57):
```yaml
- name: Install mod_wsgi python package
  pip:
    name: mod_wsgi
    version: "{{ mod_wsgi_version }}"
    executable: "{{ ansible_facts['deploy_helper']['new_release_path'] }}/pyenv/bin/pip"
    chdir: "{{ ansible_facts['deploy_helper']['new_release_path'] }}/app"
    umask: "0022"
```

**Notable**: Uses version pinning (`mod_wsgi_version` default: `5.0.0`)

### 3.3 tasks/install_uv.yml (Already implemented)

**Path**: `tasks/install_uv.yml`

**Responsibilities**: Download and install UV binary from GitHub releases with SHA256 verification

**Key facts**:
- UV version controlled by `uv_version` variable (default: `0.9.22`)
- Installs to `uv_install_dir` (default: `/usr/local/bin`)
- Supports x86_64 and aarch64 architectures
- Verifies SHA256 checksum from GitHub release
- Installs both `uv` and `uvx` binaries
- Idempotent: checks installed version, only downloads if different

**Execution conditional**: `when: miarecweb_install_uv | bool` (default: `true`)

### 3.4 tasks/preflight.yml (Python version detection)

**Path**: `tasks/preflight.yml`

**Responsibilities**: Load OS-specific variables, validate required parameters, detect/validate Python version

**Key outputs**:
- `python_version` - Full version string (e.g., `3.12.1`)
- `python_version_base` - Major.minor (e.g., `3.12`)
- Validates Python version is within `python_minimum_version` (3.10) to `python_maximum_version` (3.12)

**Python detection logic** (lines 156-183):
- If `python_version` has major.minor (e.g., `3.12`), looks for `python3.12`
- If `python_version` is just major (e.g., `3`) or empty, uses `python3`
- Runs `python --version` and parses output

### 3.5 tasks/main.yml (Task orchestration)

**Path**: `tasks/main.yml`

**Execution order**:
1. `preflight.yml` - Variable loading, validation, Python detection
2. `dependencies.yml` - OS package installation
3. `install_uv.yml` - UV binary installation (when `miarecweb_install_uv: true`)
4. Group/TLS setup
5. `deploy_helper` initialization
6. `miarecweb.yml` - Package installation
7. `upgrade_db.yml` - Database migrations
8. `apache.yml` - Apache/mod_wsgi configuration
9. `celeryd.yml`, `celerybeat.yml` - Celery services
10. `deploy_helper` finalization

**Key invariant**: UV is installed (step 3) before `miarecweb.yml` runs (step 6). This guarantees `{{ uv_install_dir }}/uv` is available.

### 3.6 defaults/main.yml (Variables)

**Path**: `defaults/main.yml`

**UV-related variables** (lines 117-131):
```yaml
miarecweb_install_uv: true
uv_version: "0.9.22"
uv_install_dir: /usr/local/bin
uv_download_base_url: "https://github.com/astral-sh/uv/releases/download"
uv_verify_checksum: true
```

**Python-related variables** (lines 5-21):
```yaml
python_version: ""  # Auto-detected if empty
python_minimum_version: "3.10"
python_maximum_version: "3.12"
python_install_dir: "{{ '/usr/local' if (python_install_from_source | default(false) | bool) else '/usr' }}"
```

**mod_wsgi variables** (lines 88-95):
```yaml
mod_wsgi_version: 5.0.0
mod_wsgi_processes: "{{ ansible_processor_vcpus | default(ansible_processor_count) }}"
mod_wsgi_threads: 5
```

## 4. Data Flow (As-Is)

### Package Installation Flow (current pip-based)

```
preflight.yml
    |
    v
[Detect Python version] --> python_version_base (e.g., "3.12")
    |
    v
install_uv.yml
    |
    v
[Download/install UV binary] --> /usr/local/bin/uv
    |
    v
miarecweb.yml
    |
    +---> [Download tarball] --> /tmp/miarecweb-X.Y.Z.N.tar.gz
    |
    +---> [Extract] --> /opt/miarecweb/releases/X.Y.Z.N/app/
    |
    +---> [python -m venv] --> /opt/miarecweb/releases/X.Y.Z.N/pyenv/
    |
    +---> [pip upgrade] --> pip, setuptools upgraded in venv
    |
    +---> [pip install -r requirements.txt] --> dependencies installed
    |
    +---> [pip install -e .] --> miarecweb installed (editable)
    |
    v
apache.yml
    |
    +---> [pip install mod_wsgi] --> mod_wsgi installed in venv
    |
    +---> [mod_wsgi-express module-location] --> path to .so file
```

### Environment Variables Passed

- `PATH`: `{{ postgresql_bin_directory }}:{{ ansible_env.PATH }}` - Required for `pg_config` during psycopg2 build

## 5. Extension Points / Integration Surfaces (As-Is)

### Where UV commands will attach

1. **Venv creation**: Replace `python -m venv` with `uv venv`
   - Location: `tasks/miarecweb.yml:68-72`
   - UV command: `{{ uv_install_dir }}/uv venv --python {{ python_version_base }} --no-python-downloads {{ pyenv_path }}`

2. **Package installation**: Replace pip with `uv pip install`
   - Location: `tasks/miarecweb.yml:91-96`
   - UV command: `{{ uv_install_dir }}/uv pip install -e . --python {{ pyenv_path }}/bin/python`

3. **mod_wsgi installation**: Replace pip with `uv pip install`
   - Location: `tasks/apache.yml:51-57`
   - UV command: `{{ uv_install_dir }}/uv pip install mod_wsgi=={{ mod_wsgi_version }} --python {{ pyenv_path }}/bin/python`

### Constraints imposed by existing interfaces

1. **umask 0022**: All shell commands must preserve this pattern for world-readable file permissions
2. **creates argument**: Idempotence relies on checking for existence of specific files
3. **PATH environment**: `pg_config` must be in PATH for psycopg2 build (UV respects environment variables)
4. **Ansible pip module**: Currently uses Ansible's `pip` module for requirements.txt - will switch to `shell` or `command` with UV (depends on whether `umask 0022 &&` prefix is needed)

## 6. Candidate Incorporation Paths (Observational)

### Path A: Direct UV replacement (preferred)

**Where it would live**: Same locations as current pip commands in `miarecweb.yml` and `apache.yml`

**Approach**:
- Replace `python -m venv` with `uv venv --python VERSION --no-python-downloads PATH`
- Remove pip upgrade task entirely
- Remove requirements.txt installation task
- Replace `pip install -e .` with `uv pip install -e . --python PATH`
- Replace `pip install mod_wsgi` with `uv pip install mod_wsgi==VERSION --python PATH`

**Pros**:
- Minimal structural changes to existing tasks
- Maintains current idempotence patterns (creates argument)
- Easy to understand diff

**Cons**:
- Uses shell/command module instead of Ansible's pip module
- Less Ansible-native

**Assumptions**:
- `uv pip install -e .` reads dependencies from miarecweb's `pyproject.toml` (inside extracted tarball) for UV-based packages
- `uv pip install -e .` works with `setup.py` + `requirements.txt` for setuptools-based packages (backward compatibility)

**Unknowns/risks**:
- mod_wsgi installation may require pip fallback (spec mentions this as potential issue)

### Path B: Conditional UV/pip switching

**Where it would live**: Same files, with `when` conditions based on UV availability

**Approach**:
- Keep existing pip-based tasks
- Add parallel UV-based tasks with `when: uv_available`
- Let user choose via variable

**Pros**:
- Backward compatibility guaranteed
- Gradual rollout possible

**Cons**:
- Code duplication
- More complex maintenance
- Against spec (spec says UV is required, not optional)

## 7. Tests & Tooling (As-Is)

### Test frameworks

- **Molecule**: Test orchestration framework for Ansible roles
- **Testinfra**: Python-based infrastructure testing (pytest plugin)
- **Docker**: Container driver for molecule tests

### Existing test scenarios

| Scenario | Purpose | Default miarecweb version |
|----------|---------|---------------------------|
| `default` | Full role test | 2025.12.2.15 (setuptools-based) |
| `tls` | TLS certificate configuration | 2025.12.2.15 |
| `uv` | UV binary installation only | N/A (tags: uv) |
| `uv_upgrade` | UV version upgrade | N/A |

### CI configuration (.github/workflows/ci.yml)

**Jobs**:
1. `lint`: Runs `uv run ansible-lint`
2. `test`: Matrix of molecule tests

**Test matrix** (distro x scenario):
- `default`: ubuntu2204, ubuntu2404, rockylinux8, rockylinux9, rhel8, rhel9
- `tls`: ubuntu2204, ubuntu2404, rockylinux9, rhel9
- `uv`: ubuntu2404, rockylinux9
- `uv_upgrade`: ubuntu2404

**Environment variables**:
- `MOLECULE_MIARECWEB_VERSION`: From GitHub vars `${{ vars.MIARECWEB_VERSION }}`
- `MOLECULE_PYTHON_VERSION`: From matrix (3 or 3.12)

### Testinfra tests

**molecule/default/tests/test_defaults.py**:
- `test_directories()`: Verifies `/opt/miarecweb/releases/VERSION` exists
- `test_files()`: Verifies production.ini, systemd services, log files
- `test_service()`: Verifies celeryd, celerybeat, apache are running
- `test_socket()`: Verifies ports 80/443 are listening
- `test_health_endpoint()`: Curls `/health` endpoint, checks JSON response
- `test_script()`: Runs `create_root_user` script to verify Python venv works

**molecule/uv/tests/test_uv.py**:
- `test_uv_binaries_installed()`: Verifies uv/uvx exist with correct permissions
- `test_uv_reports_expected_version()`: Verifies `uv --version` output

### Linters/formatters

- **ansible-lint**: Configured in `.ansible-lint`

### Ansible version constraint

From the role's `pyproject.toml` (development dependencies for this Ansible role, not miarecweb):
```toml
"ansible>=9.0,<10.0"
```
Pinned to ansible 9.x (ansible-core 2.16) to support EL8 distros with Python 3.6.

**Note**: The miarecweb application has its own `pyproject.toml` inside the tarball that gets downloaded and extracted to `/opt/miarecweb/releases/X.Y.Z.N/app/`. That file defines miarecweb's dependencies and is what `uv pip install -e .` will read.

## 8. Open Questions

1. **Testing with both miarecweb versions**: The spec requires testing with both setuptools-based (2025.12.2.15) and UV-based (2025.12.2.373) packages. Current CI only tests one version per run. Need to verify CI variables or add matrix entries.

2. **mod_wsgi fallback**: Spec defers mod_wsgi fallback to implementation phase. Will `uv pip install mod_wsgi` work, or is pip-in-venv fallback needed?

3. **Idempotence marker file**: Current implementation uses `.dist-info` directory as idempotence marker. UV may create this differently. Need to verify the exact path created by `uv pip install -e .`

## 9. Evidence Appendix

### Files read

| File | Lines | Key findings |
|------|-------|--------------|
| `tasks/miarecweb.yml` | 1-291 | Lines 68-96 are modification targets |
| `tasks/apache.yml` | 1-184 | Lines 51-57 for mod_wsgi |
| `tasks/preflight.yml` | 1-196 | Python detection at lines 156-183 |
| `tasks/install_uv.yml` | 1-169 | UV installation already implemented |
| `tasks/main.yml` | 1-125 | Task execution order |
| `tasks/dependencies.yml` | 1-100 | OS dependencies |
| `defaults/main.yml` | 1-230 | UV variables at 117-131 |
| `vars/Debian.yml` | 1-11 | Apache paths |
| `vars/RedHat.yml` | 1-11 | Apache paths |
| `.github/workflows/ci.yml` | 1-119 | Test matrix |
| `molecule/default/molecule.yml` | 1-34 | Test config |
| `molecule/default/tests/test_defaults.py` | 1-86 | Testinfra tests |
| `molecule/uv/tests/test_uv.py` | 1-31 | UV tests |
| `pyproject.toml` | 1-23 | Role's dev dependencies (ansible, molecule, etc.) |

### Key code locations

| Component | File:Line | Symbol/Task |
|-----------|-----------|-------------|
| Venv creation | `tasks/miarecweb.yml:68` | "Create python virtual environment" |
| Pip upgrade | `tasks/miarecweb.yml:74` | "Upgrade PIP and setuptools" |
| Requirements install | `tasks/miarecweb.yml:81` | "Install dependencies (requirements.txt)" |
| Package install | `tasks/miarecweb.yml:91` | "Install MiaRecWeb" |
| mod_wsgi install | `tasks/apache.yml:51` | "Install mod_wsgi python package" |
| UV install | `tasks/install_uv.yml:75` | "uv \| Install or upgrade uv" |
| Python detection | `tasks/preflight.yml:156` | "Detect Python version" block |
| UV version var | `defaults/main.yml:122` | `uv_version: "0.9.22"` |
| UV install dir var | `defaults/main.yml:125` | `uv_install_dir: /usr/local/bin` |
