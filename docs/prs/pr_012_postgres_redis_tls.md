## Summary

Add TLS/SSL connection support for PostgreSQL and Redis, enabling encrypted and optionally mutually-authenticated (mTLS) connections to database services.

---

## Purpose

This change enables secure database connections in environments that require TLS encryption for compliance or security requirements. It supports:
- Server certificate validation (verify-ca, verify-full)
- Client certificate authentication (mTLS)
- Flexible SSL mode configuration for PostgreSQL
- Redis TLS with configurable certificate requirements

---

## Testing

* [x] Added/updated tests
* [x] Ran `uv run ansible-lint` (1 minor warning in test infrastructure)
* Notes:
  - New `molecule/tls` scenario tests full mTLS configuration
  - Tests verify TLS certificates, production.ini configuration, health endpoints, and alembic connectivity
  - Tested on Ubuntu 24.04 and Rocky Linux 9

---

## Related Issues

N/A

---

## Changes

### New Variables (defaults/main.yml)

**PostgreSQL TLS:**
- `miarecweb_db_tls` - Enable TLS (default: false)
- `miarecweb_db_tls_sslmode` - SSL mode: disable, allow, prefer, require, verify-ca, verify-full (default: verify-ca)
- `miarecweb_db_tls_ca_file` - CA certificate path
- `miarecweb_db_tls_cert_file` - Client certificate path (for mTLS)
- `miarecweb_db_tls_key_file` - Client private key path (for mTLS)

**Redis TLS:**
- `miarecweb_redis_tls` - Enable TLS (default: false)
- `miarecweb_redis_tls_ca_file` - CA certificate path
- `miarecweb_redis_tls_cert_file` - Client certificate path (for mTLS)
- `miarecweb_redis_tls_key_file` - Client private key path (for mTLS)
- `miarecweb_redis_tls_cert_reqs` - Certificate requirement: required, optional, none (default: required)
- `miarecweb_redis_tls_check_hostname` - Verify server hostname (default: false)

### Role Changes

- **Preflight validation** - Validates TLS certificate files exist before deployment
- **Security enforcement** - Requires non-root celery user when using client certificates
- **Permission management** - Sets appropriate group ownership on TLS private keys
- **Configuration generation** - Writes DATABASE_SSL_PARAMS and REDIS_SSL_PARAMS to production.ini
- **Database migrations** - Passes TLS environment variables to alembic commands

### Test Infrastructure

- New `molecule/tls` scenario with full mTLS testing
- CA and client certificate generation
- PostgreSQL and Redis TLS server configuration
- Comprehensive test coverage for TLS connectivity

---

## Notes for Reviewers

1. **Breaking change consideration**: When TLS with client certificates is enabled, the role now requires `miarecweb_celery_user` to be set to a non-root user and `miarec_bin_group` to be configured. This ensures the celery worker can read the private key files.

2. **Certificate management**: This role provisions TLS parameters but does NOT manage certificate deployment. Certificates must be pre-deployed to the target system before running this role.

3. **Redis schema change**: When `miarecweb_redis_tls` is enabled, the Redis connection URL scheme changes from `redis://` to `rediss://`.

4. **ansible-lint warning**: One minor `risky-shell-pipe` warning in `molecule/tls/tasks/redis_tls.yml:120` - this is in test infrastructure only, not the main role.

---

## Docs

* [x] N/A (internal role, no external documentation required)
* [ ] Updated relevant documentation
