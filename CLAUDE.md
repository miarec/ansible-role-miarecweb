This file provides guidance to coding agent when working with code in this repository.

## Project Overview

This is an Ansible role (`ansible-role-miarecweb`) for deploying the MiaRec Web application. It installs and configures the web application along with its dependencies: Apache/mod_wsgi, Celery worker, and Celery beat scheduler.

## Common Commands

### Linting
```bash
uv run ansible-lint
```

### Running Molecule Tests
```bash
# Basic test (default: ubuntu2404)
uv run molecule test

# Test with specific distro and version
MOLECULE_DISTRO=ubuntu2204 MOLECULE_MIARECWEB_VERSION=2024.1.0.0 uv run molecule test

# Test with verbosity
MOLECULE_ANSIBLE_VERBOSITY=3 uv run molecule test
```

### Running Individual Stages
For development and debugging, run individual molecule stages:

```bash
# Create container
MOLECULE_DISTRO=ubuntu2404 uv run molecule create

# Prepare (install Python, PostgreSQL, Redis, Apache)
MOLECULE_DISTRO=ubuntu2404 uv run molecule prepare

# Converge (run the role)
MOLECULE_DISTRO=ubuntu2404 uv run molecule converge

# Verify (run tests)
MOLECULE_DISTRO=ubuntu2404 uv run molecule verify

# Idempotence check
MOLECULE_DISTRO=ubuntu2404 uv run molecule idempotence

# Destroy container
MOLECULE_DISTRO=ubuntu2404 uv run molecule destroy

# Login for debugging
MOLECULE_DISTRO=ubuntu2404 uv run molecule login
```

### Available Molecule Environment Variables
- `MOLECULE_DISTRO`: OS container (ubuntu2204, ubuntu2404, rockylinux9, rhel9)
- `MOLECULE_MIARECWEB_VERSION`: Version to install (default: 2024.1.0.0)
- `MOLECULE_MIARECWEB_SECRET`: Secret key (default: secret)
- `MOLECULE_PYTHON_VERSION`: Python version to install/use (default: 3.12)
- `MOLECULE_ANSIBLE_VERBOSITY`: 0-3 (default: 0)

## Role Architecture

### Task Execution Flow (tasks/main.yml)
1. `preflight.yml` - Pre-run validation
2. `dependencies.yml` - Install OS dependencies
3. Python version verification
4. `miarecweb.yml` - Install/upgrade web app files using deploy_helper
5. `upgrade_db.yml` - Database schema migrations (when `miarecweb_upgrade_db: true`)
6. `apache.yml` - Apache/mod_wsgi configuration (when `miarecweb_install_apache: true`)
7. `celeryd.yml` - Celery worker setup (when `miarecweb_install_celeryd: true`)
8. `celerybeat.yml` - Celery beat scheduler (when `miarecweb_install_celerybeat: true`)
9. Release finalization with deploy_helper (keeps 10 releases)

### Installation Directory Structure
```
/opt/miarecweb/
├── releases/        # Versioned releases
│   └── X.Y.Z.N/
├── shared/          # Shared resources across releases
└── current -> releases/X.Y.Z.N  # Symlink to active release
```

### OS-Specific Variables
- `vars/RedHat.yml` - RHEL/Rocky Linux settings (httpd, apache user)
- `vars/Debian.yml` - Ubuntu/Debian settings (apache2, www-data user)

### Key Dependencies
- Python 3.10-3.12 (pre-installed, version auto-detected or specified by `python_version`)
- PostgreSQL client libraries (version specified by `postgresql_version`)
- Apache with mod_wsgi
- Redis (connection configured, not installed by this role)

## Important Variables

Required:
- `miarecweb_version`: Version to install
- `miarecweb_secret`: Encryption key for database secrets (must persist across upgrades)
- `postgresql_version`: PostgreSQL version for pg_config binary location

Python configuration:
- `python_version`: Python version (auto-detected if not specified)
  - Can be "3.12", "3.12.1", or "3" (major only uses system python3)
  - If specified with major.minor (e.g., "3.12"), will look for python3.12 first
- `python_minimum_version`: Minimum supported version (default: 3.10)
- `python_maximum_version`: Maximum supported version (default: 3.12)

Multi-server deployment:
- `miarecweb_install_apache`: Enable for web servers only
- `miarecweb_install_celeryd`: Enable for worker servers only
- `miarecweb_install_celerybeat`: Enable on single server only (scheduler)
- `miarecweb_upgrade_db`: Run once per cluster when upgrading multiple servers
