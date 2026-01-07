# TLS Support for PostgreSQL and Redis Connections - Implementation Plan

## Overview

Add TLS connection support for PostgreSQL and Redis databases in the MiaRecWeb Ansible role, with Molecule tests to verify functionality. This enables secure encrypted connections between the MiaRecWeb application and its database/cache backends.

## Current State Analysis

### What Exists Now
- Basic PostgreSQL connection via `miarecweb_db_*` variables
- Basic Redis connection via `miarecweb_redis_*` variables
- Molecule `default` scenario for non-TLS testing
- Reference TLS implementations in sibling roles (ansible-postgresql, ansible-role-pgbouncer, ansible-role-redis)

### What's Missing
- PostgreSQL TLS configuration variables
- Redis TLS configuration variables
- TLS certificate file validation in preflight
- DATABASE_SSL_PARAMS configuration in production.ini
- REDIS_SCHEMA and REDIS_SSL_PARAMS configuration in production.ini
- TLS environment variables for psql in upgrade_db.yml
- Dedicated `molecule/tls` scenario

## Desired End State

After implementation:
1. Role supports PostgreSQL connections with TLS (server verification and optional mTLS)
2. Role supports Redis connections with TLS (server verification and optional mTLS)
3. Both TLS and non-TLS deployments work correctly
4. Molecule TLS scenario validates TLS connectivity end-to-end
5. Database migrations (alembic) work over TLS connections

### Verification Commands
```bash
# Default scenario (non-TLS) passes
MOLECULE_DISTRO=ubuntu2404 uv run molecule test

# TLS scenario passes
MOLECULE_DISTRO=ubuntu2404 uv run molecule test -s tls
MOLECULE_DISTRO=rockylinux9 uv run molecule test -s tls
```

## What We're NOT Doing

- **Automatic port switching**: User must configure correct port when Redis uses different TLS port
- **Certificate generation**: Role does not generate certificates; expects pre-existing cert files
- **Redis Sentinel/Cluster TLS**: Only standalone Redis TLS is covered
- **PostgreSQL connection pooling TLS**: PgBouncer TLS is handled by the pgbouncer role

## Implementation Approach

The implementation follows the pattern established in sibling roles:
1. Add TLS variables with sensible defaults (TLS disabled by default)
2. Add preflight validation for certificate files
3. Configure application connection strings conditionally
4. Create separate molecule scenario for TLS testing

---

## Phase 1: Add TLS Variables

### Overview
Define all TLS-related configuration variables with documentation.

### Changes Required

#### File: `defaults/main.yml`

Add PostgreSQL TLS variables after database pool settings (around line 46):

```yaml
# -----------------------------
# PostgreSQL TLS settings
# -----------------------------
miarecweb_db_tls: false
miarecweb_db_tls_sslmode: verify-ca
# TLS mode options:
#   disable - Plain TCP, TLS not requested
#   allow - Try plain TCP first, then TLS if rejected
#   prefer - Try TLS first, fall back to plain TCP (default if sslmode not set)
#   require - TLS required, no server cert validation
#   verify-ca - TLS required, validate server cert against CA
#   verify-full - TLS required, validate server cert and hostname
miarecweb_db_tls_ca_file: ""       # CA certificate to validate server
miarecweb_db_tls_cert_file: ""     # Client certificate for mTLS
miarecweb_db_tls_key_file: ""      # Client private key for mTLS
```

Add Redis TLS variables after Redis settings (around line 75):

```yaml
# -----------------------------
# Redis TLS settings
# -----------------------------
miarecweb_redis_tls: false
miarecweb_redis_tls_ca_file: ""           # CA certificate to validate server
miarecweb_redis_tls_cert_file: ""         # Client certificate for mTLS
miarecweb_redis_tls_key_file: ""          # Client private key for mTLS
miarecweb_redis_tls_cert_reqs: required   # required, optional, or none
miarecweb_redis_tls_check_hostname: false # Verify server hostname
```

### Success Criteria

#### Automated Verification:
- [ ] `uv run ansible-lint` passes without errors on defaults/main.yml
- [ ] Variables are properly documented with comments

---

## Phase 2: Add Preflight Validation

### Overview
Validate that TLS certificate files exist when TLS is enabled.

### Changes Required

#### File: `tasks/preflight.yml`

Add after the illegal character check (around line 26):

```yaml
# ---------------------------------------------
# Validate TLS certificate files
# ---------------------------------------------
- name: Validate PostgreSQL TLS CA file exists
  stat:
    path: "{{ miarecweb_db_tls_ca_file }}"
  register: _db_tls_ca_stat
  when:
    - miarecweb_db_tls | bool
    - miarecweb_db_tls_ca_file | length > 0

- name: Fail if PostgreSQL TLS CA file not found
  fail:
    msg: "PostgreSQL TLS CA file not found: {{ miarecweb_db_tls_ca_file }}"
  when:
    - miarecweb_db_tls | bool
    - miarecweb_db_tls_ca_file | length > 0
    - _db_tls_ca_stat.stat is defined
    - not _db_tls_ca_stat.stat.exists

# Similar blocks for:
# - miarecweb_db_tls_cert_file
# - miarecweb_db_tls_key_file
# - miarecweb_redis_tls_ca_file
# - miarecweb_redis_tls_cert_file
# - miarecweb_redis_tls_key_file
```

### Success Criteria

#### Automated Verification:
- [ ] `uv run ansible-lint` passes on tasks/preflight.yml
- [ ] Role fails with clear message when TLS enabled but cert file missing

---

## Phase 3: Configure TLS in production.ini

### Overview
Add TLS connection parameters to the application configuration file.

### Changes Required

#### File: `tasks/miarecweb.yml`

Add after the main production.ini configuration block:

```yaml
# Configure PostgreSQL TLS settings
- name: Configure DATABASE_SSL_PARAMS in production.ini
  lineinfile:
    dest: "{{ ansible_facts['deploy_helper']['new_release_path'] }}/production.ini"
    regexp: '^DATABASE_SSL_PARAMS = '
    line: "DATABASE_SSL_PARAMS = {{ _db_ssl_params }}"
  vars:
    _db_ssl_params: >-
      {%- set params = [] -%}
      {%- if miarecweb_db_tls | bool -%}
        {%- set params = params + ['sslmode=' + miarecweb_db_tls_sslmode] -%}
        {%- if miarecweb_db_tls_ca_file -%}
          {%- set params = params + ['sslrootcert=' + miarecweb_db_tls_ca_file] -%}
        {%- endif -%}
        {%- if miarecweb_db_tls_cert_file -%}
          {%- set params = params + ['sslcert=' + miarecweb_db_tls_cert_file] -%}
        {%- endif -%}
        {%- if miarecweb_db_tls_key_file -%}
          {%- set params = params + ['sslkey=' + miarecweb_db_tls_key_file] -%}
        {%- endif -%}
      {%- endif -%}
      {{ params | join('&') }}
  notify:
    - reload apache
    - reload celeryd
    - reload celerybeat

# Configure Redis TLS settings
- name: Configure REDIS_SCHEMA in production.ini
  lineinfile:
    dest: "{{ ansible_facts['deploy_helper']['new_release_path'] }}/production.ini"
    regexp: '^REDIS_SCHEMA = '
    line: "REDIS_SCHEMA = {{ 'rediss' if miarecweb_redis_tls | bool else 'redis' }}"
  notify:
    - reload apache
    - reload celeryd
    - reload celerybeat

- name: Configure REDIS_SSL_PARAMS in production.ini
  lineinfile:
    dest: "{{ ansible_facts['deploy_helper']['new_release_path'] }}/production.ini"
    regexp: '^REDIS_SSL_PARAMS = '
    line: "REDIS_SSL_PARAMS = {{ _redis_ssl_params }}"
  vars:
    _redis_ssl_params: >-
      {%- set params = [] -%}
      {%- if miarecweb_redis_tls | bool -%}
        {%- set params = params + ['ssl_cert_reqs=' + miarecweb_redis_tls_cert_reqs] -%}
        {%- set params = params + ['ssl_check_hostname=' + (miarecweb_redis_tls_check_hostname | string)] -%}
        {%- if miarecweb_redis_tls_ca_file -%}
          {%- set params = params + ['ssl_ca_certs=' + miarecweb_redis_tls_ca_file] -%}
        {%- endif -%}
        {%- if miarecweb_redis_tls_cert_file -%}
          {%- set params = params + ['ssl_certfile=' + miarecweb_redis_tls_cert_file] -%}
        {%- endif -%}
        {%- if miarecweb_redis_tls_key_file -%}
          {%- set params = params + ['ssl_keyfile=' + miarecweb_redis_tls_key_file] -%}
        {%- endif -%}
      {%- endif -%}
      {{ params | join('&') }}
  notify:
    - reload apache
    - reload celeryd
    - reload celerybeat
```

### Success Criteria

#### Automated Verification:
- [ ] `uv run ansible-lint` passes on tasks/miarecweb.yml
- [ ] With TLS disabled: DATABASE_SSL_PARAMS is empty, REDIS_SCHEMA is "redis"
- [ ] With TLS enabled: DATABASE_SSL_PARAMS contains sslmode and cert paths, REDIS_SCHEMA is "rediss"

---

## Phase 4: Update Database Upgrade Script

### Overview
Add TLS environment variables to the psql command for database ANALYZE.

### Changes Required

#### File: `tasks/upgrade_db.yml`

Update the psql environment block to include TLS variables:

```yaml
- name: Update database statistics (ANALYZE)
  command: 'psql -c "ANALYZE"'
  environment:
    PGUSER: "{{ miarecweb_db_user }}"
    PGPASSWORD: "{{ miarecweb_db_password }}"
    PGDATABASE: "{{ miarecweb_db_name }}"
    PGHOST: "{{ miarecweb_db_host }}"
    PGPORT: "{{ miarecweb_db_port }}"
    PGSSLMODE: "{{ miarecweb_db_tls_sslmode if miarecweb_db_tls | bool else 'disable' }}"
    PGSSLROOTCERT: "{{ miarecweb_db_tls_ca_file if (miarecweb_db_tls | bool and miarecweb_db_tls_ca_file) else '' }}"
    PGSSLCERT: "{{ miarecweb_db_tls_cert_file if (miarecweb_db_tls | bool and miarecweb_db_tls_cert_file) else '' }}"
    PGSSLKEY: "{{ miarecweb_db_tls_key_file if (miarecweb_db_tls | bool and miarecweb_db_tls_key_file) else '' }}"
  when: 'alembic_current_revision is defined and " (head)" not in alembic_current_revision'
  run_once: "{{ miarecweb_upgrade_db_once|default(True) }}"
```

### Success Criteria

#### Automated Verification:
- [ ] `uv run ansible-lint` passes on tasks/upgrade_db.yml
- [ ] psql command works with TLS when connecting to TLS-enabled PostgreSQL

---

## Phase 5: Create Molecule TLS Scenario

### Overview
Create a dedicated molecule scenario that tests TLS connectivity.

### New Files Required

#### molecule/tls/molecule.yml
```yaml
---
dependency:
  name: galaxy
  options:
    requirements-file: ../default/collections.yml
driver:
  name: docker
platforms:
  - name: miarecweb-tls-${MOLECULE_DISTRO:-ubuntu2404}
    image: ghcr.io/miarec/${MOLECULE_DISTRO:-ubuntu2404}-systemd:latest
    volumes:
      - /sys/fs/cgroup:/sys/fs/cgroup:rw
    cgroupns_mode: host
    privileged: true
    pre_build_image: true

provisioner:
  name: ansible
  env:
    ANSIBLE_VERBOSITY: ${MOLECULE_ANSIBLE_VERBOSITY:-0}
    ANSIBLE_ROLES_PATH: ${MOLECULE_PROJECT_DIRECTORY}/../
    MIARECWEB_VERSION: ${MOLECULE_MIARECWEB_VERSION:-"2025.12.2.2"}
    MIARECWEB_SECRET: ${MOLECULE_MIARECWEB_SECRET:-"secret"}
    PYTHON_VERSION: ${MOLECULE_PYTHON_VERSION:-"3.12"}

verifier:
  name: testinfra
  options:
    s: true
    verbose: true

scenario:
  name: tls
  test_sequence:
    - destroy
    - create
    - prepare
    - converge
    - verify
    - destroy
```

#### molecule/tls/prepare.yml
```yaml
---
- name: Prepare TLS Environment
  hosts: all
  become: true

  tasks:
    - name: Set python_version from environment
      set_fact:
        python_version: "{{ lookup('env', 'PYTHON_VERSION') }}"

    - name: Include Python installation tasks
      include_tasks: ../default/tasks/python.yml

    - name: Include TLS certificate generation tasks
      include_tasks: tasks/certificates.yml

    - name: Include PostgreSQL TLS setup tasks
      include_tasks: tasks/postgresql_tls.yml

    - name: Include Redis TLS setup tasks
      include_tasks: tasks/redis_tls.yml

    - name: Include Apache installation tasks
      include_tasks: ../default/tasks/apache.yml
```

#### molecule/tls/converge.yml
```yaml
---
- name: Converge
  hosts: all
  become: true

  pre_tasks:
    - set_fact:
        miarecweb_version: "{{ lookup('env', 'MIARECWEB_VERSION') }}"
        miarecweb_secret: "{{ lookup('env', 'MIARECWEB_SECRET') }}"
        python_version: "{{ lookup('env', 'PYTHON_VERSION') }}"

    - name: Update apt cache | Debian
      apt:
        update_cache: true
        cache_valid_time: 600
      changed_when: false
      when: ansible_facts['os_family'] == "Debian"

  roles:
    - role: ansible-role-miarecweb
      vars:
        # PostgreSQL TLS configuration
        miarecweb_db_tls: true
        miarecweb_db_tls_sslmode: verify-ca
        miarecweb_db_tls_ca_file: /etc/miarecweb/tls/ca.crt
        miarecweb_db_tls_cert_file: /etc/miarecweb/tls/client.crt
        miarecweb_db_tls_key_file: /etc/miarecweb/tls/client.key
        # Redis TLS configuration
        miarecweb_redis_tls: true
        miarecweb_redis_tls_ca_file: /etc/miarecweb/tls/ca.crt
        miarecweb_redis_tls_cert_file: /etc/miarecweb/tls/client.crt
        miarecweb_redis_tls_key_file: /etc/miarecweb/tls/client.key
        miarecweb_redis_tls_cert_reqs: required
        miarecweb_redis_tls_check_hostname: false
```

#### molecule/tls/tasks/certificates.yml
Generate CA, server, and client certificates using OpenSSL.

Key requirements:
- CA key (4096-bit RSA)
- Server certificate signed by CA with SAN for localhost/127.0.0.1
- Client certificate signed by CA for mTLS

#### molecule/tls/tasks/postgresql_tls.yml
- Install PostgreSQL from system packages
- Copy server certificates to PostgreSQL data directory
- Configure postgresql.conf with ssl=on and certificate paths
- Configure pg_hba.conf with `hostssl` (reject non-TLS connections)
- Set `clientcert=verify-ca` to require client certificates
- Create miarec user and miarecdb database

#### molecule/tls/tasks/redis_tls.yml
- Install Redis from system packages
- Copy server certificates to Redis directory
- Configure Redis with `port 0` and `tls-port 6379`
- Configure `tls-auth-clients optional` (or `yes` for strict mTLS)
- Configure certificate file paths

#### molecule/tls/tests/test_tls.py
```python
def test_tls_certificates_exist(host):
    """Verify TLS certificates were generated."""
    # Check CA, server, and client certs exist

def test_production_ini_db_ssl_params(host):
    """Verify DATABASE_SSL_PARAMS is configured correctly."""
    # Check sslmode, sslrootcert, sslcert, sslkey

def test_production_ini_redis_ssl_params(host):
    """Verify Redis TLS settings are configured."""
    # Check REDIS_SCHEMA=rediss, ssl_ca_certs, ssl_certfile, ssl_keyfile

def test_postgresql_ssl_enabled(host):
    """Verify PostgreSQL has SSL enabled."""
    # Run: sudo -u postgres psql -tAc "SHOW ssl;"

def test_redis_tls_listening(host):
    """Verify Redis is listening on TLS port."""
    # Check socket tcp://127.0.0.1:6379

def test_script(host):
    """Verify miarecweb can connect to databases with TLS."""
    # Run create_root_user script - validates both DB and Redis connectivity
```

### Success Criteria

#### Automated Verification:
- [ ] `MOLECULE_DISTRO=ubuntu2404 uv run molecule test -s tls` passes
- [ ] `MOLECULE_DISTRO=rockylinux9 uv run molecule test -s tls` passes
- [ ] PostgreSQL rejects non-TLS connections (hostssl in pg_hba.conf)
- [ ] Redis rejects non-TLS connections (port 0, tls-port 6379)
- [ ] Application successfully connects via TLS (test_script passes)

#### Manual Verification:
- [ ] Review production.ini contains correct TLS parameters
- [ ] Verify certificates have correct permissions

---

## Testing Strategy

### Unit Tests (Automated)
- ansible-lint on all modified files
- Molecule default scenario (backward compatibility)
- Molecule TLS scenario

### Integration Tests (Automated)
- test_script verifies end-to-end DB connectivity with TLS
- PostgreSQL SSL status check (`SHOW ssl;`)
- Redis TLS port listening check

### Manual Testing Steps
1. Deploy to test environment with TLS disabled - verify normal operation
2. Deploy to test environment with TLS enabled - verify TLS connectivity
3. Verify PostgreSQL connection string in production.ini
4. Verify Redis connection uses `rediss://` scheme

---

## Files Summary

### Role Files to Modify
| File | Changes |
|------|---------|
| `defaults/main.yml` | Add PostgreSQL and Redis TLS variables |
| `tasks/preflight.yml` | Add TLS certificate file validation |
| `tasks/miarecweb.yml` | Configure DATABASE_SSL_PARAMS, REDIS_SCHEMA, REDIS_SSL_PARAMS |
| `tasks/upgrade_db.yml` | Add PGSSLMODE and related environment variables |

### New Molecule TLS Scenario Files
| File | Purpose |
|------|---------|
| `molecule/tls/molecule.yml` | Scenario configuration |
| `molecule/tls/prepare.yml` | TLS setup orchestration |
| `molecule/tls/converge.yml` | Role invocation with TLS vars |
| `molecule/tls/tasks/certificates.yml` | CA and certificate generation |
| `molecule/tls/tasks/postgresql_tls.yml` | PostgreSQL with TLS config |
| `molecule/tls/tasks/redis_tls.yml` | Redis with TLS config |
| `molecule/tls/tests/test_tls.py` | TLS verification tests |

---

## Progress

- [x] Phase 1: Add TLS Variables - COMPLETED
- [x] Phase 2: Add Preflight Validation - COMPLETED
- [x] Phase 3: Configure TLS in production.ini - COMPLETED
- [x] Phase 4: Update Database Upgrade Script - COMPLETED
- [x] Phase 5: Create Molecule TLS Scenario - COMPLETED

## Surprises & Discoveries

1. **Reference implementations available**: Sibling roles (ansible-postgresql, ansible-role-pgbouncer, ansible-role-redis) have established TLS patterns that were followed.

2. **PostgreSQL path differences**: Debian uses `/etc/postgresql/VERSION/CLUSTER/` while RedHat uses `/var/lib/pgsql/data/` - need to detect dynamically.

3. **Redis service naming**: Debian uses `redis-server`, RedHat uses `redis` - handled via OS-specific facts.

4. **Client certificate verification**: PostgreSQL uses `clientcert=verify-ca` in pg_hba.conf, Redis uses `tls-auth-clients` option.

## Decision Log

| Decision | Rationale |
|----------|-----------|
| Use `miarecweb_db_tls_*` prefix | Consistent with existing `miarecweb_db_*` variables |
| Default TLS to `false` | Backward compatibility - existing deployments unaffected |
| Use `verify-ca` as default sslmode | Balance of security (server verification) without hostname strictness |
| Separate molecule scenario | Clean separation, doesn't add complexity to default tests |
| `tls-auth-clients optional` for Redis | Allows connection with or without client certs during testing |
| Empty string for optional cert paths | Jinja2 conditionals skip empty values in connection strings |

## Outcomes & Retrospective

*To be completed after implementation*

- [ ] All tests pass on ubuntu2404 and rockylinux9
- [ ] No regressions in default (non-TLS) scenario
- [ ] Documentation updated if needed

---

## References

- Original requirements: `docs/plans/2025-12-postgres-redis-tls/initial_prompt.md`
- Draft plan: `docs/plans/2025-12-postgres-redis-tls/draft_plan.md`
- PostgreSQL SSL documentation: https://www.postgresql.org/docs/current/ssl-tcp.html
- Redis TLS documentation: https://redis.io/docs/management/security/encryption/
- Reference: `../ansible-postgresql/molecule/tls/`
- Reference: `../ansible-role-pgbouncer/molecule/tls-full/`
- Reference: `../ansible/ansible-role-redis/molecule/tls/`
