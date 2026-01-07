# TLS Support for PostgreSQL and Redis Connections

## Summary
Add TLS connection support for PostgreSQL and Redis databases in the MiaRecWeb Ansible role, with Molecule tests to verify functionality.

## Initial Requirements Review

The initial requirements in `docs/plans/2025-12-postgres-redis-tls/initial_prompt.md` define:

### Proposed Variables

**PostgreSQL TLS:**
```yaml
miarecweb_postgres_tls: false
miarecweb_postgres_tls_sslmode: verify-ca
miarecweb_postgres_tls_ca_file: ""
miarecweb_postgres_tls_key_file: ""
miarecweb_postgres_tls_cert_file: ""
```

**Redis TLS:**
```yaml
miarecweb_redis_tls: false
miarecweb_redis_tls_ca_file: ""
miarecweb_redis_tls_key_file: ""
miarecweb_redis_tls_cert_file: ""
miarecweb_redis_tls_cert_reqs: required
miarecweb_redis_tls_check_hostname: false
```

### Configuration Output
- PostgreSQL: `DATABASE_SSL_PARAMS = sslmode=verify-ca&sslcert=...&sslkey=...&sslrootcert=...`
- Redis: `REDIS_SCHEMA = rediss` and `REDIS_SSL_PARAMS = ssl_cert_reqs=...&ssl_certfile=...`

---

## Identified Gaps and Edge Cases

### 1. Variable Naming Inconsistency
**Issue:** Proposed variables use `miarecweb_postgres_*` but existing PostgreSQL variables use `miarecweb_db_*` prefix.

**Recommendation:** Use `miarecweb_db_tls*` prefix for consistency with existing variables:
```yaml
miarecweb_db_tls: false
miarecweb_db_tls_sslmode: verify-ca
miarecweb_db_tls_ca_file: ""
miarecweb_db_tls_key_file: ""
miarecweb_db_tls_cert_file: ""
```

### 2. Database Upgrade Script (upgrade_db.yml) Missing TLS Support
**Issue:** The `tasks/upgrade_db.yml` uses `psql` with environment variables (PGUSER, PGPASSWORD, PGDATABASE, PGHOST, PGPORT) but doesn't include TLS settings.

**Required additions for TLS:**
```yaml
environment:
  PGSSLMODE: "{{ miarecweb_db_tls_sslmode }}"
  PGSSLCERT: "{{ miarecweb_db_tls_cert_file }}"
  PGSSLKEY: "{{ miarecweb_db_tls_key_file }}"
  PGSSLROOTCERT: "{{ miarecweb_db_tls_ca_file }}"
```

### 3. Redis TLS Port Not Addressed
**Issue:** Redis typically uses port 6379 for non-TLS and 6380 for TLS. The initial requirements don't mention this.

**Options:**
- A) Assume user changes `miarecweb_redis_port` manually when enabling TLS
- B) Add a separate `miarecweb_redis_tls_port` variable
- C) Document that users must update the port when Redis runs TLS on a different port

**Recommendation:** Option A - Keep it simple, user configures the correct port for their setup.

### 4. Certificate File Validation Missing
**Issue:** No preflight validation for:
- Certificate files exist when TLS is enabled
- Private key files have correct permissions (should be readable by application)
- Certificate paths don't contain special characters

**Recommendation:** Add preflight checks in `tasks/preflight.yml`:

```yaml
- name: Validate PostgreSQL TLS certificate files exist
  when: miarecweb_db_tls | bool
  block:
    - stat:
        path: "{{ item }}"
      loop:
        - "{{ miarecweb_db_tls_ca_file }}"
      when: item | length > 0
      register: _tls_files
    - fail:
        msg: "TLS certificate file not found: {{ item.item }}"
      loop: "{{ _tls_files.results }}"
      when: item.stat is defined and not item.stat.exists
```

### 5. Molecule Test Scenario Structure
**Issue:** Initial requirements mention `molecule/tls/prepare.yml` but only `molecule/default` scenario exists.

**Options:**
- A) Create a new `molecule/tls` scenario dedicated to TLS testing
- B) Add TLS testing to the existing `molecule/default` scenario
- C) Use environment variables to conditionally enable TLS in default scenario

**Recommendation:** Option A - Create a separate `molecule/tls` scenario for cleaner separation. The default scenario remains unchanged for basic testing.

### 6. Client Certificates (mTLS) Complexity
**Issue:** The initial requirements include client certificate parameters (`tls_key_file`, `tls_cert_file`), which implies mutual TLS (mTLS). This is more complex:
- Server verifies client certificate
- Client verifies server certificate
- Both PostgreSQL and Redis need to be configured to request client certificates

**Recommendation:** Support both modes:

- **Server TLS only:** Only CA file needed to verify server
- **mTLS:** CA file + client key + client cert

For PostgreSQL `sslmode`:
- `require` - Encrypt only, no server verification
- `verify-ca` - Encrypt + verify server cert (server TLS)
- `verify-full` - Encrypt + verify server cert + hostname (server TLS)

Client certs are optional and used for client authentication regardless of sslmode.

### 7. pg_hba.conf for Molecule TLS Tests
**Issue:** Current molecule `tasks/postgresql.yml` configures pg_hba.conf with `host` connection type:
```
host    miarecdb        miarec          127.0.0.1/32            md5
```

For TLS testing, this needs to be `hostssl`:
```
hostssl miarecdb        miarec          127.0.0.1/32            md5
```

Additionally, forbid explicitly non-ssl connections.

### 8. Redis TLS Configuration in Molecule

**Issue:** Current molecule `tasks/redis.yml` doesn't configure Redis for TLS.

**Required for TLS testing:**
- Generate Redis server certificate
- Configure Redis with TLS settings in `/etc/redis/redis.conf`
- Start Redis on TLS port

### 9. Test Verification
**Issue:** Current `molecule/default/tests/test_defaults.py` doesn't verify database/Redis connectivity.

**Recommendation:** Add TLS-specific verification tests:
- Verify PostgreSQL TLS connection works
- Verify Redis TLS connection works
- Verify the application can connect (the existing `test_script` partially covers this)

### 10. Empty String vs Undefined Certificate Paths
**Issue:** Initial requirements use empty strings `""` as defaults for certificate paths. Need to handle:

- Empty string = not provided (skip in connection string)
- Non-empty = include in connection string

**Recommendation:** Build SSL_PARAMS conditionally:
```jinja2
{% set params = [] %}
{% if miarecweb_db_tls_sslmode %}
{% set params = params + ['sslmode=' + miarecweb_db_tls_sslmode] %}
{% endif %}
{% if miarecweb_db_tls_ca_file %}
{% set params = params + ['sslrootcert=' + miarecweb_db_tls_ca_file] %}
{% endif %}
# ... etc
DATABASE_SSL_PARAMS = {{ params | join('&') }}
```

### 11. Redis SSL Parameter Names
**Issue:** Redis-py uses different parameter names than documented:

- `ssl_cert_reqs` -> valid values: `required`, `optional`, `none` (or CERT_REQUIRED, CERT_OPTIONAL, CERT_NONE)
- `ssl_check_hostname` -> boolean
- `ssl_certfile` -> client certificate path
- `ssl_keyfile` -> client key path
- `ssl_ca_certs` -> CA certificate path

Verify these match what MiaRecWeb application expects.

### 12. Password with Special Characters in TLS Context
**Issue:** Existing preflight check prevents `%` in passwords. With TLS certificate paths added to connection strings, need to ensure paths don't contain characters that break URL encoding.

**Recommendation:** Add validation for certificate paths in preflight.

---

## Design Decisions (Confirmed)

1. **Variable naming:** Use `miarecweb_db_tls_*` prefix (consistent with existing `miarecweb_db_*` variables)
2. **Molecule tests:** Create new `molecule/tls` scenario (separate from default)
3. **mTLS scope:** Full mTLS support from the start (client certificates included)
4. **Redis port:** User configures correct port manually (no auto-detection)

---

## Implementation Plan

### Step 1: Add TLS Variables to defaults/main.yml

Add after existing database pool settings (line ~46):

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

Add after existing Redis settings (line ~58):

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

### Step 2: Add TLS Validation to tasks/preflight.yml

Add after the illegal character check (line ~26):

```yaml
# Validate PostgreSQL TLS configuration
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
    - not _db_tls_ca_stat.stat.exists

# Validate Redis TLS configuration
- name: Validate Redis TLS CA file exists
  stat:
    path: "{{ miarecweb_redis_tls_ca_file }}"
  register: _redis_tls_ca_stat
  when:
    - miarecweb_redis_tls | bool
    - miarecweb_redis_tls_ca_file | length > 0

- name: Fail if Redis TLS CA file not found
  fail:
    msg: "Redis TLS CA file not found: {{ miarecweb_redis_tls_ca_file }}"
  when:
    - miarecweb_redis_tls | bool
    - miarecweb_redis_tls_ca_file | length > 0
    - not _redis_tls_ca_stat.stat.exists
```

### Step 3: Update tasks/miarecweb.yml for TLS Configuration

Add after existing production.ini configuration (after line ~183):

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

### Step 4: Update tasks/upgrade_db.yml for TLS

Update the psql environment block (line ~40-45) to include TLS:

```yaml
  environment:
    PGUSER: "{{ miarecweb_db_user }}"
    PGPASSWORD: "{{ miarecweb_db_password }}"
    PGDATABASE: "{{ miarecweb_db_name }}"
    PGHOST: "{{ miarecweb_db_host }}"
    PGPORT: "{{ miarecweb_db_port }}"
    PGSSLMODE: "{{ miarecweb_db_tls_sslmode if miarecweb_db_tls | bool else 'disable' }}"
    PGSSLROOTCERT: "{{ miarecweb_db_tls_ca_file if miarecweb_db_tls | bool else '' }}"
    PGSSLCERT: "{{ miarecweb_db_tls_cert_file if miarecweb_db_tls | bool else '' }}"
    PGSSLKEY: "{{ miarecweb_db_tls_key_file if miarecweb_db_tls | bool else '' }}"
```

### Step 5: Create molecule/tls Scenario

#### molecule/tls/molecule.yml
```yaml
---
dependency:
  name: galaxy
driver:
  name: docker
platforms:
  - name: miarecweb-tls-${MOLECULE_DISTRO:-ubuntu2404}
    image: ghcr.io/miarec/${MOLECULE_DISTRO:-ubuntu2404}-systemd:latest
    pre_build_image: true
    privileged: true
    cgroupns_mode: host
provisioner:
  name: ansible
  env:
    MIARECWEB_VERSION: ${MIARECWEB_VERSION:-2025.12.2.2}
    MIARECWEB_SECRET: ${MIARECWEB_SECRET:-secret}
    PYTHON_VERSION: ${PYTHON_VERSION:-3.12}
  config_options:
    defaults:
      verbosity: ${MOLECULE_ANSIBLE_VERBOSITY:-0}
verifier:
  name: testinfra
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

    - include_tasks: ../default/tasks/python.yml
    - include_tasks: tasks/certificates.yml
    - include_tasks: tasks/postgresql_tls.yml
    - include_tasks: tasks/redis_tls.yml
    - include_tasks: ../default/tasks/apache.yml
```

#### molecule/tls/tasks/certificates.yml
Generate CA and certificates for PostgreSQL and Redis server/client authentication.

#### molecule/tls/tasks/postgresql_tls.yml
Configure PostgreSQL with TLS enabled and `hostssl` in pg_hba.conf.

#### molecule/tls/tasks/redis_tls.yml
Configure Redis with TLS certificates and enable TLS listener.

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
  roles:
    - role: ansible-role-miarecweb
      vars:
        miarecweb_db_tls: true
        miarecweb_db_tls_sslmode: verify-ca
        miarecweb_db_tls_ca_file: /etc/miarecweb/tls/ca.crt
        miarecweb_db_tls_cert_file: /etc/miarecweb/tls/client.crt
        miarecweb_db_tls_key_file: /etc/miarecweb/tls/client.key
        miarecweb_redis_tls: true
        miarecweb_redis_tls_ca_file: /etc/miarecweb/tls/ca.crt
        miarecweb_redis_tls_cert_file: /etc/miarecweb/tls/client.crt
        miarecweb_redis_tls_key_file: /etc/miarecweb/tls/client.key
        miarecweb_redis_tls_cert_reqs: required
        miarecweb_redis_port: 6379  # Use same port with TLS in test
```

#### molecule/tls/verify.yml
Verify TLS connections work (use testinfra or shell commands to test connectivity).

---

## Files to Modify

### Role Files:
| File | Changes |
|------|---------|
| `defaults/main.yml` | Add PostgreSQL and Redis TLS variables |
| `tasks/preflight.yml` | Add TLS certificate file validation |
| `tasks/miarecweb.yml` | Configure DATABASE_SSL_PARAMS, REDIS_SCHEMA, REDIS_SSL_PARAMS |
| `tasks/upgrade_db.yml` | Add PGSSLMODE and related environment variables |

### New Molecule TLS Scenario:
| File | Purpose |
|------|---------|
| `molecule/tls/molecule.yml` | Scenario configuration |
| `molecule/tls/prepare.yml` | TLS setup orchestration |
| `molecule/tls/converge.yml` | Role invocation with TLS vars |
| `molecule/tls/verify.yml` | TLS verification tests |
| `molecule/tls/tasks/certificates.yml` | CA and certificate generation |
| `molecule/tls/tasks/postgresql_tls.yml` | PostgreSQL with TLS config |
| `molecule/tls/tasks/redis_tls.yml` | Redis with TLS config |

---

## Success Criteria

1. Role deploys successfully with TLS disabled (backward compatible)
2. Role deploys successfully with PostgreSQL TLS enabled
3. Role deploys successfully with Redis TLS enabled
4. `molecule test -s tls` passes on ubuntu2404 and rockylinux9
5. Application can connect to PostgreSQL over TLS (verified via test_script)
6. Application can connect to Redis over TLS (verified via test_script)
7. Database upgrade (alembic) works with TLS enabled

## Important notes

When TLS is used, both PostgreSQL and Redis servers should be configured to accept only TLS connections. TCP connections should be explicitely rejected.
The servers should be configured to verify client's certificates (must be signed with CA certificate).
The miarecweb application should use sslmode=verify-ca for PostgreSQL connection and "require" for Redis connection.
Hostname should not be verified.

In testinfra, do a verification that TLS is configured properly in PostgreSQL and Redis (see reference roles below).



## Reference implementations

We have ansible roles that have tests TLS molecule tests:

- [Postgresql role](../ansible-postgresql)
- [PGbouncer role](../ansible-role-pgbouncer) - Molecule test in this role shows how to setup PostgreSQL from package, generate certificates (both servers and clients) and configure PostgreSQL with TLS enabled.
- [Redis role](../ansible-role-redis)- This role shows how to install Redis from package and configure TLS on server side and use `redis-cli PING` for testing.





