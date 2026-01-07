# Install miarecweb with UV — Specification

## 1. Context & Goals (User/Business Perspective)

- **Problem statement**: The miarecweb package (version 2025.12.2.373+) has migrated from pip to UV. The `requirements.txt` file has been removed from the package distribution. The current Ansible role still uses pip and depends on `requirements.txt`, which will break with newer miarecweb versions.

- **Who it helps**: DevOps engineers deploying miarecweb on production systems.

- **Goals**:
  - Replace pip-based virtual environment creation and package installation with UV
  - Maintain the same directory structure (`/opt/miarecweb/releases/VERSION/pyenv`)
  - Continue to support Python version specification via `python_version` variable
  - Install miarecweb package in editable mode using `uv pip install -e .`
  - Maintain idempotence of the role

## 2. Non-Goals / Out of Scope

- **UV installation**: Already implemented in PR #14 (`tasks/install_uv.yml`). This task assumes UV is available at `{{ uv_install_dir }}/uv`.
- **Python installation**: The role already handles Python version detection/validation in `preflight.yml`. No changes needed.
- **Separate requirements.txt installation**: The current two-step process (`pip install -r requirements.txt` then `pip install -e .`) was for debugging convenience only. With UV, use single command `uv pip install -e .` which installs all dependencies from pyproject.toml.

### Backward Compatibility

- The role should work with both old setuptools-based miarecweb packages (e.g., 2025.12.2.15) and new UV-based packages (e.g., 2025.12.2.373+).
- `uv pip install -e .` handles both formats automatically.
- Test with both versions to verify.

### mod_wsgi Installation

- mod_wsgi will also migrate to UV: `uv pip install mod_wsgi`
- If that fails, fallback to: install pip into venv (`uv pip install pip`) then `uv run pip install mod_wsgi`

## 3. Definitions / Glossary

| Term | Definition |
|------|------------|
| UV | Fast Python package manager by Astral, drop-in replacement for pip |
| venv | Python virtual environment |
| editable install | Installing a package in development mode (`-e .`) so changes to source are reflected without reinstall |
| pyproject.toml | Modern Python package configuration file (PEP 517/518) |
| setuptools | Traditional Python build system using setup.py |

## 4. Functional Requirements

### 4.1 User stories

- As a DevOps engineer, I want to deploy miarecweb using UV so that installation is faster and compatible with newer miarecweb versions.
- As a DevOps engineer, I want the role to work with both old (setuptools) and new (UV) miarecweb packages so I can upgrade incrementally.

### 4.2 Use cases

- **UC1: Fresh install** - Install miarecweb on a new server. UV creates venv, installs package and dependencies in one step.
- **UC2: Upgrade** - Upgrade existing miarecweb. New release directory created, UV installs into new venv, symlink switched.
- **UC3: Specify Python version** - User sets `python_version: "3.12"`, UV uses that Python for venv creation.
- **UC4: Auto-detect Python** - User doesn't set `python_version`, role auto-detects, passes detected version to UV.

### 4.3 Tasks to modify

| Current Task | Change |
|--------------|--------|
| `miarecweb.yml:68-72` - Create venv with `python -m venv` | Replace with `uv venv --python VERSION --no-python-downloads PATH` |
| `miarecweb.yml:74-79` - Upgrade pip/setuptools | Remove (not needed with UV) |
| `miarecweb.yml:81-89` - Install requirements.txt | Remove (merged into package install) |
| `miarecweb.yml:91-96` - Install miarecweb with pip | Replace with `uv pip install -e . --python PATH` |
| `apache.yml:51-57` - Install mod_wsgi with pip | Replace with `uv pip install mod_wsgi --python PATH` |

### 4.4 Edge cases & failure modes

- **UV not installed**: Role should fail with clear message: "uv binaries are not available on this machine, re-run this role with `-t uv` to install it"
- **Python version not found**: UV can automatically download Python if not found. Use `--no-python-downloads` flag to disable this and rely on system Python. Existing `preflight.yml` validation ensures requested Python version is installed.
- **Idempotence**: Use `creates:` argument to skip venv creation and package install if already done.

### 4.5 File Permissions (umask)

- The role must work on systems with restrictive umask (e.g., 027).
- Continue using `umask 0022 &&` prefix for shell commands (same approach as current pip implementation).
- Installed files must be world-readable so Apache/mod_wsgi can access them.

## 5. Non-Functional Requirements

- **Performance**: UV is 10-100x faster than pip. Installation should be noticeably faster.
- **Security**: No changes to security posture. UV binary is already verified via SHA256 checksum in `install_uv.yml`.
- **Reliability**: Role must pass Molecule tests on all supported distros (ubuntu2204, ubuntu2404, rockylinux8, rockylinux9).
- **Observability**: Ansible task output will show UV commands and their results. No additional logging needed.

## 6. UX / API Contracts

No changes to role interface. Existing variables continue to work:
- `python_version` - Python version to use (auto-detected if not set)
- `miarecweb_version` - Version of miarecweb to install
- `uv_install_dir` - Location of UV binary (default: `/usr/local/bin`)

## 7. Data & State

No changes to directory structure:
```
/opt/miarecweb/
├── releases/
│   └── X.Y.Z.N/
│       ├── app/           # Extracted miarecweb source
│       ├── pyenv/         # Python virtual environment (created by UV)
│       ├── production.ini
│       └── cache/
└── current -> releases/X.Y.Z.N
```

## 8. Acceptance Criteria (Top-level)

- [ ] Virtual environment created using `uv venv --python VERSION --no-python-downloads PATH`
- [ ] miarecweb package installed using `uv pip install -e . --python PATH`
- [ ] mod_wsgi installed using `uv pip install mod_wsgi --python PATH`
- [ ] No pip upgrade step (removed - not needed with UV)
- [ ] No separate requirements.txt installation (merged into package install)
- [ ] Files have correct permissions (world-readable) via `umask 0022`
- [ ] Role is idempotent (second run makes no changes)
- [ ] Role works with old setuptools-based miarecweb (2025.12.2.15)
- [ ] Role works with new UV-based miarecweb (2025.12.2.373)
- [ ] Clear error message when UV is not installed
- [ ] `uv run ansible-lint` passes with no errors

### Testing

- Run Molecule tests with `MOLECULE_MIARECWEB_VERSION=2025.12.2.373` (UV-based)
- Run Molecule tests with `MOLECULE_MIARECWEB_VERSION=2025.12.2.15` (setuptools-based)
- Test on: ubuntu2204, ubuntu2404, rockylinux8, rockylinux9
- Verify idempotence check passes

## 9. Open Questions

1. **mod_wsgi fallback needed?** - Should we implement the fallback (`uv pip install pip` then `uv run pip install mod_wsgi`) or try `uv pip install mod_wsgi` first and only add fallback if it fails during testing?
   - **Resolution**: Deferred to implementation phase. Try direct `uv pip install mod_wsgi` first. Add fallback only if testing reveals issues.

## 10. Assumptions

- UV is installed before `miarecweb.yml` runs (guaranteed by task order in `main.yml`)
- `python_version_base` fact (e.g., "3.12") is set by `preflight.yml` before miarecweb tasks run
- The miarecweb tarball contains `pyproject.toml` (for UV-based versions) or `setup.py` + `requirements.txt` (for setuptools-based versions)
- `uv pip install -e .` handles both package formats

## 11. References

- [UV Documentation](https://docs.astral.sh/uv/)
- [UV Python Versions](https://docs.astral.sh/uv/concepts/python-versions/) - covers `--no-python-downloads` flag
- [UV pip compatibility](https://docs.astral.sh/uv/pip/compatibility/)
- PR #14: `docs/prs/pr_014_install_uv.md` - UV installation implementation
- Original idea: `docs/plans/2026-01-install-with-uv/idea.md`
