# TLS connections to Postgres and Redis

## Goal

Configure the application to use TLS connections when connecting to Postgres and Redis databases.

And cover with Molecule tests.


## New ansible role variables:

PostgreSQL TLS connection settings:

```yaml
miarecweb_postgres_tls: false
miarecweb_postgres_tls_sslmode: verify-ca
# TLS mode to use for connections to PostgreSQL servers.
# disable - Plain TCP. TLS is not even requested from the server.
# allow - First try plain TCP. If server rejects it, try TLS. Server certificate is not validated.
# prefer - First try TLS. If server rejects it, fall back to plain TCP. Server certificate is not validated. Default.
# require - Connection must go over TLS. If server rejects it, plain TCP is not attempted. Server certificate is not validated.
# verify-ca - Connection must go over TLS and server certificate must be valid according to server_tls_ca_file. Server host name is not checked against certificate.
# verify-full - Connection must go over TLS and server certificate must be valid according to server_tls_ca_file. Server host name must match certificate information.

miarecweb_postgres_tls_ca_file: ""         # Root certificate file to validate PostgreSQL server certificates.
miarecweb_postgres_tls_key_file: ""        # Private key for PgBouncer to authenticate against PostgreSQL server
miarecweb_postgres_tls_cert_file: ""       # Certificate for private key. PostgreSQL server can validate it.
```

Redis TLS connection settings:

```yaml
miarecweb_redis_tls: false
miarecweb_redis_tls_ca_file: ""            # Root certificate file to validate Redis server certificates.
miarecweb_redis_tls_key_file: ""           # Private key for MiaRecWeb to authenticate against Redis server
miarecweb_redis_tls_cert_file: ""          # Certificate for private key. Redis server can validate it.
miarecweb_redis_tls_cert_reqs: required    # Certificate requirements for Redis TLS connection. One of: required, optional, none.
miarecweb_redis_tls_check_hostname: false  # Whether to verify Redis server hostname against certificate.
```


## MiaRecWeb application configuration file (production.ini)

This file is provisioned by the Ansible role.

By default, TLS is disabled for both Postgres and Redis connections.
See the comments in the file for details on how to enable and configure TLS connections.

### PostgreSQL section:

```ini
[DEFAULT]
# ==================================
# PostgreSQL Database Configuration
# ==================================
# PostgreSQL accepts both SSL and non-SSL connections on the same port (5432)
# Connection type is determined by sslmode parameter in the connection string
#
# To enable SSL, configure DATABASE_SSL_PARAMS below.
#
# For non-SSL connection: Use sslmode=disable (default mode is "prefer")
# For SSL connection: Use sslmode=require (or verify-ca/verify-full)
#
# Note: On Windows, 127.0.0.1 is preferred over 'localhost' due to 1s TCP connection delay
DATABASE_HOST = 127.0.0.1
DATABASE_PORT = 5432

# PostgreSQL SSL/TLS Configuration
# =================================
# Certificate files:
#   - /path/to/client.crt: Client certificate (signed by CA)
#   - /path/to/client.key: Client private key (chmod 600)
#   - /path/to/ca.crt: Trusted Certificate Authority certificate (for server certificate verification)
#
# SSL Mode Options (sslmode parameter):
#   - disable: Never use SSL (no encryption)
#   - allow: First try non-SSL, then SSL
#   - prefer: First try SSL, then non-SSL (this is a default mode, if sslmode is not specified)
#   - require: Always use SSL (no server cert verification)
#   - verify-ca: Always use SSL, verify server cert is signed by trusted CA
#   - verify-full: Always use SSL, verify server cert and server's hostname match
#
# For SSL connections, add these parameters to the DATABASE_SSL_PARAMS connection string:
#
# Example SSL connection configurations:
# --------------------------------------
#
# 1. SSL with server certificate verification (recommended for production):
# DATABASE_SSL_PARAMS = sslmode=verify-ca&sslcert=/path/to/client.crt&sslkey=/path/to/client.key&sslrootcert=/path/to/ca.crt
#
# 2. Disable SSL
# DATABASE_SSL_PARAMS = sslmode=disable
#
# 3. Default model. If sslmode is not configured in the connection string, then a default mode ("prefer") is used
# DATABASE_SSL_PARAMS=

DATABASE_SSL_PARAMS =
```

To enable TLS, set the `DATABASE_SSL_PARAMS` variable accordingly.

### Redis section:

```ini
[DEFAULT]
# ==================================
# Redis Connection Configuration
# ================================
# Redis server uses separate ports for SSL and non-SSL connections (assuming both are enabled).
# Note: On Windows, 127.0.0.1 is preferred over 'localhost' due to 1s TCP connection delay
REDIS_HOST = 127.0.0.1
REDIS_PORT = 6379

# Redis SSL/TLS Configuration
# =================================
# Certificate files:
#   - /path/to/client.crt: Client certificate (signed by CA)
#   - /path/to/client.key: Client private key (chmod 600)
#   - /path/to/ca.crt: Trusted Certificate Authority certificate (for server certificate verification)
#
# SSL Mode Options (ssl_cert_reqs parameter):
#  - required: Strict verification (most secure)
#  - optional: Validates if provided but not strict
#  - none: No verification (least secure, not recommended)
#
# Other SSL parameters:
#  - ssl_check_hostname (bool): Verify server's hostname (i.e. the hostname in the server's certificate should match to REDIS_HOST)
#
# For SSL connections, add these parameters to the REDIS_SSL_PARAMS connection string:

# Example SSL connection configurations:
# --------------------------------------
# 1. SSL is disabled
# REDIS_SCHEMA = redis
# REDIS_SSL_PARAMS =

# 2. SSL with server certificate verification (recommended for production):
# ==================================================
#
# REDIS_SCHEMA = rediss
# REDIS_SSL_PARAMS = ssl_cert_reqs=optional&ssl_check_hostname=False&ssl_certfile=/path/to/client.crt&ssl_keyfile=/path/to/client.key&ssl_ca_certs=/path/to/ca.crt

REDIS_SCHEMA = redis
REDIS_SSL_PARAMS =
```

To enable TLS, set the `REDIS_SCHEMA` to `rediss` and configure the `REDIS_SSL_PARAMS` variable accordingly.


## Molecule Testing

Generate TLS cerificates for Postgres and Redis in the `molecule/tls/prepare.yml`.

Example for PostgreSQL certificates:

```yaml

# file prepare.yml

---
- name: Prepare PostgreSQL with TLS and TLS certificates for PGBouncer
  hosts: all
  become: true

  vars:
    test_db_user: testuser
    test_db_password: testpassword
    test_db_name: testdb
    pgbouncer_tls_dir: /etc/pgbouncer/tls
    postgresql_tls_dir: /etc/postgresql/tls
    pgbouncer_user: "{{ 'pgbouncer' if ansible_facts['os_family'] == 'RedHat' else 'postgres' }}"
    pgbouncer_group: "{{ pgbouncer_user }}"
    postgres_user: postgres
    postgres_group: postgres

  tasks:
    - name: Install OpenSSL
      package:
        name: openssl
        state: present

    # Create postgres user/group first for certificate ownership
    - name: Create PostgreSQL group
      group:
        name: "{{ postgres_group }}"
        state: present

    - name: Create PostgreSQL user
      user:
        name: "{{ postgres_user }}"
        group: "{{ postgres_group }}"
        shell: /bin/false
        system: true
        create_home: false

    # Generate TLS certificates for PostgreSQL
    - name: Create PostgreSQL TLS certificate directory
      file:
        path: "{{ postgresql_tls_dir }}"
        state: directory
        mode: "0755"

    - name: Generate CA private key
      command: openssl genrsa -out {{ postgresql_tls_dir }}/ca.key 4096
      args:
        creates: "{{ postgresql_tls_dir }}/ca.key"

    - name: Generate CA certificate
      command: >
        openssl req -x509 -new -nodes
        -key {{ postgresql_tls_dir }}/ca.key
        -sha256 -days 365
        -out {{ postgresql_tls_dir }}/ca.crt
        -subj "/CN=Test-CA"
      args:
        creates: "{{ postgresql_tls_dir }}/ca.crt"

    - name: Generate PostgreSQL server private key
      command: openssl genrsa -out {{ postgresql_tls_dir }}/server.key 2048
      args:
        creates: "{{ postgresql_tls_dir }}/server.key"

    - name: Generate PostgreSQL server CSR
      command: >
        openssl req -new
        -key {{ postgresql_tls_dir }}/server.key
        -out {{ postgresql_tls_dir }}/server.csr
        -subj "/CN=localhost"
      args:
        creates: "{{ postgresql_tls_dir }}/server.csr"

    - name: Sign PostgreSQL server certificate with CA
      command: >
        openssl x509 -req
        -in {{ postgresql_tls_dir }}/server.csr
        -CA {{ postgresql_tls_dir }}/ca.crt
        -CAkey {{ postgresql_tls_dir }}/ca.key
        -CAcreateserial
        -out {{ postgresql_tls_dir }}/server.crt
        -days 365 -sha256
      args:
        creates: "{{ postgresql_tls_dir }}/server.crt"

    - name: Set proper permissions on CA key
      file:
        path: "{{ postgresql_tls_dir }}/ca.key"
        mode: "0600"

    # PostgreSQL requires the server private key to be owned by the
    # PostgreSQL service user and not be group/world readable
    - name: Set proper permissions on PostgreSQL server key
      file:
        path: "{{ postgresql_tls_dir }}/server.key"
        mode: "0600"
        owner: "{{ postgres_user }}"
        group: "{{ postgres_group }}"

    - name: Set proper permissions on certificates
      file:
        path: "{{ item }}"
        mode: "0644"
      loop:
        - "{{ postgresql_tls_dir }}/ca.crt"
        - "{{ postgresql_tls_dir }}/server.crt"

    # Debian/Ubuntu installation
    - name: Install PostgreSQL (Debian/Ubuntu)
      when: ansible_facts['os_family'] == "Debian"
      block:
        - name: Update apt cache
          apt:
            update_cache: true
            cache_valid_time: 600
          changed_when: false

        - name: Install PostgreSQL packages
          apt:
            name:
              - postgresql
              - postgresql-contrib
              - postgresql-client
              - python3-psycopg2
            state: present

    # RedHat/Rocky installation
    - name: Install PostgreSQL (RedHat/Rocky)
      when: ansible_facts['os_family'] == "RedHat"
      block:
        - name: Install PostgreSQL packages
          yum:
            name:
              - postgresql-server
              - postgresql-contrib
              - python3-psycopg2
            state: present

        - name: Check if PostgreSQL is initialized
          stat:
            path: /var/lib/pgsql/data/pg_hba.conf
          register: pg_hba_conf

        - name: Initialize PostgreSQL database
          command: postgresql-setup --initdb
          changed_when: true
          when: not pg_hba_conf.stat.exists

    # Configure PostgreSQL paths
    - name: Find PostgreSQL config directory (Debian)
      when: ansible_facts['os_family'] == "Debian"
      block:
        - name: Get PostgreSQL version directory
          shell: set -o pipefail && ls -1 /etc/postgresql/ | head -1
          args:
            executable: /bin/bash
          register: pg_version
          changed_when: false

        - name: Set PostgreSQL paths for Debian
          set_fact:
            pg_conf_file: "/etc/postgresql/{{ pg_version.stdout }}/main/postgresql.conf"
            pg_hba_file: "/etc/postgresql/{{ pg_version.stdout }}/main/pg_hba.conf"

    - name: Set PostgreSQL paths for RedHat
      when: ansible_facts['os_family'] == "RedHat"
      set_fact:
        pg_conf_file: "/var/lib/pgsql/data/postgresql.conf"
        pg_hba_file: "/var/lib/pgsql/data/pg_hba.conf"

    # Configure PostgreSQL with TLS
    - name: Enable SSL in PostgreSQL
      lineinfile:
        path: "{{ pg_conf_file }}"
        regexp: "^#?ssl\\s*="
        line: "ssl = on"
        state: present
      notify: Restart PostgreSQL

    - name: Configure SSL certificate file
      lineinfile:
        path: "{{ pg_conf_file }}"
        regexp: "^#?ssl_cert_file\\s*="
        line: "ssl_cert_file = '{{ postgresql_tls_dir }}/server.crt'"
        state: present
      notify: Restart PostgreSQL

    - name: Configure SSL key file
      lineinfile:
        path: "{{ pg_conf_file }}"
        regexp: "^#?ssl_key_file\\s*="
        line: "ssl_key_file = '{{ postgresql_tls_dir }}/server.key'"
        state: present
      notify: Restart PostgreSQL

    - name: Configure SSL CA file
      lineinfile:
        path: "{{ pg_conf_file }}"
        regexp: "^#?ssl_ca_file\\s*="
        line: "ssl_ca_file = '{{ postgresql_tls_dir }}/ca.crt'"
        state: present
      notify: Restart PostgreSQL

    # Start PostgreSQL service
    - name: Start and enable PostgreSQL service
      service:
        name: postgresql
        state: started
        enabled: true

    - name: Flush handlers to restart PostgreSQL with TLS
      meta: flush_handlers

    # Set password_encryption to md5 BEFORE creating users
    - name: Set password_encryption to md5 for PGBouncer compatibility
      become: true
      become_user: postgres
      community.postgresql.postgresql_set:
        name: password_encryption
        value: md5
      notify: Reload PostgreSQL

    - name: Flush handlers to apply password_encryption setting
      meta: flush_handlers

    - name: Create test database
      become: true
      become_user: postgres
      community.postgresql.postgresql_db:
        name: "{{ test_db_name }}"
        state: present

    # Create user with explicit md5-compatible password
    - name: Create test user with password
      become: true
      become_user: postgres
      community.postgresql.postgresql_user:
        name: "{{ test_db_user }}"
        password: "{{ test_db_password }}"
        state: present

    - name: Grant privileges to test user
      become: true
      become_user: postgres
      community.postgresql.postgresql_privs:
        database: "{{ test_db_name }}"
        privs: ALL
        type: database
        role: "{{ test_db_user }}"

    # Configure pg_hba for TLS connections (hostssl) with md5
    - name: Configure pg_hba.conf for TLS md5 authentication from localhost
      community.postgresql.postgresql_pg_hba:
        dest: "{{ pg_hba_file }}"
        contype: hostssl
        databases: all
        users: all
        source: 127.0.0.1/32
        method: md5
        state: present
      notify: Reload PostgreSQL

```

TODO: Create client TLS certificates for MiaRecWeb to connect to Postgres.
TODO: Create TLS certificates for Redis server and client.

