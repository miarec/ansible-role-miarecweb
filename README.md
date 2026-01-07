# ansible-miarecweb
![CI](https://github.com/miarec/ansible-role-miarecweb/actions/workflows/ci.yml/badge.svg?event=push)
Ansible role for installing of MiaRecWeb app.


Role Variables
--------------

- `miarecweb_version`: The version of miarecweb files to install
- `miarecweb_upgrade_db`: Option to upgrade database layout during installation (default: yes). This option is useful when multiple web application servers are deployed behind load balancer. When upgrading many web servers, it is enough to run database layout only once. But it is ok to run it multiple times as well.
- `miarecweb_install_apache`: Option to configure apache (default: yes). When using decoupled architecture, set this option to 'yes' for web hosts, and to 'no' for celery worker hosts.
- `miarecweb_install_celeryd`: Option to install celery worker (default: yes). When using decoupled architecture, set this option to 'no' for web hosts, and to 'yes' for celery worker hosts.
- `miarecweb_install_celerybeat`: Option to install celery beat schedulear (default: yes). There should be only one celery beat instance in a cluster. When using multi-server architecture, you need to enable celery beat only on a single host.
- `miarecweb_db_host`: The PostgreSQL host (default: 127.0.0.1)
- `miarecweb_db_port`: The PostgreSQL port (default: 5432)
- `miarecweb_db_name`: The PostgreSQL database name (default: miarecdb)
- `miarecweb_db_user`: The ostgreSQL database user (default: miarec)
- `miarecweb_db_password`: The PostgreSQL database password (default: password)
- `miarecweb_redis_host`: The Redis host (default: 127.0.0.1)
- `miarecweb_redis_port`: The Redis port (default: 6379)
- `python_version`: The python version to install miarecweb. Caution! The python should be installed in advance
- `python_install_dir`: The location of the installed python files (default is /usr/local)
- `postgresql_version`: The vesion of PostgreSQL to link with. Caution! The PostgreSQL should be installed in advance
- `postgresql_bin_directory`: The location of pg_config binaries
- `miarecweb_install_dir`: The installation directory (default: /opt/miarecweb)
- `miarecweb_log_dir`: The location of log files (default: /var/log/miarecweb)
- `miarecweb_secret`: A secret key used for encrypting secrets in the database

Example Playbook
----------------

eg:

``` yaml
    - name: Install miarecweb
      hosts: localhost
      become: yes
      roles:
        - role: ansible-miarecweb
          miarecweb_version: 5.2.0.2119
          python_version: 3.5.3
          postgresql_version: 9.3
```

The above playbook will install miarecweb version 5.2.0.2119.


## Testing

This role uses [Molecule](https://molecule.readthedocs.io/) with Docker for testing.
[uv](https://docs.astral.sh/uv/) is used for dependency management.

### Prerequisites

- Docker
- uv (install via `curl -LsSf https://astral.sh/uv/install.sh | sh`)

### Running Tests

```bash
# Run full test suite (default: ubuntu2404)
uv run molecule test

# Test against specific distro
MOLECULE_DISTRO=ubuntu2404 uv run molecule test
MOLECULE_DISTRO=rockylinux9 uv run molecule test
```

### Running Individual Stages

For development and debugging, you can run individual molecule stages:

```bash
# Create the container
MOLECULE_DISTRO=ubuntu2404 uv run molecule create

# Run preparation tasks (install Python, PostgreSQL, etc.)
MOLECULE_DISTRO=ubuntu2404 uv run molecule prepare

# Run the role (converge)
MOLECULE_DISTRO=ubuntu2404 uv run molecule converge

# Run tests/verification
MOLECULE_DISTRO=ubuntu2404 uv run molecule verify

# Run idempotence check
MOLECULE_DISTRO=ubuntu2404 uv run molecule idempotence

# Destroy the container
MOLECULE_DISTRO=ubuntu2404 uv run molecule destroy

# Login to the container for debugging
MOLECULE_DISTRO=ubuntu2404 uv run molecule login
```

### Available Distros

| Distribution   | Variable Value  |
|----------------|-----------------|
| Ubuntu 22.04   | `ubuntu2204`    |
| Ubuntu 24.04   | `ubuntu2404`    |
| Rocky Linux 9  | `rockylinux9`   |
| RHEL 9         | `rhel9`         |

### Running Tests in Parallel

By default, Molecule uses a shared ephemeral directory, which prevents running the same
scenario with different `MOLECULE_DISTRO` values in parallel. To run tests in parallel,
set a unique `MOLECULE_EPHEMERAL_DIRECTORY` for each distro:

```bash
# Run default scenario on both distros in parallel
MOLECULE_DISTRO=ubuntu2404 MOLECULE_EPHEMERAL_DIRECTORY="/tmp/molecule-ubuntu2404" uv run molecule test -s default &
MOLECULE_DISTRO=rockylinux9 MOLECULE_EPHEMERAL_DIRECTORY="/tmp/molecule-rockylinux9" uv run molecule test -s default &
wait
```

This works because each process gets its own inventory and state files, avoiding conflicts.

**References:**
- [Molecule CI Documentation](https://docs.ansible.com/projects/molecule/ci/)
- [GitHub Issue #1272 - Parallel testing](https://github.com/ansible/molecule/issues/1272)

### Linting

```bash
uv run ansible-lint
```

