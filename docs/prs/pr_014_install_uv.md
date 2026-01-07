## Summary

Add optional installation of `uv` and `uvx` binaries from official GitHub releases, with SHA256 checksum verification enabled by default.

---

## Purpose

This role needs `uv` (Python package manager) for dependency management. Rather than running remote install scripts (`curl | sh`), this change implements secure, deterministic binary installation directly from GitHub releases with integrity verification.

---

## Testing

How did you verify it works?

* [x] Ran `uv run ansible-lint`
* [x] Added Molecule scenarios for `uv` (fresh install) and `uv_upgrade` (upgrade from older version)

Notes:
- Molecule tests verify binary installation, permissions, and version reporting
- Idempotence is tested in both scenarios

---

## Related Issues

N/A

---

## Changes

Brief list of main changes:

* Add `tasks/install_uv.yml` - idempotent uv/uvx installation with:
  - Version-aware installation (skips if already at target version)
  - Architecture auto-detection (x86_64/aarch64)
  - SHA256 checksum verification from GitHub release assets
  - Proper cleanup of temporary files
* Add new variables in `defaults/main.yml`:
  - `miarecweb_install_uv` (default: `true`)
  - `uv_version` (default: `0.9.22`)
  - `uv_install_dir` (default: `/usr/local/bin`)
  - `uv_download_base_url`
  - `uv_verify_checksum` (default: `true`)
* Wire uv tasks into `tasks/main.yml` with tag `uv` for isolated execution
* Add `molecule/uv` scenario for fresh install testing
* Add `molecule/uv_upgrade` scenario for upgrade testing
* Add Agent Guidelines to `CLAUDE.md`

---

## Notes for Reviewers

- All uv-related tasks are tagged with `uv` for isolated execution
- The role does NOT execute any remote scripts for security
- Checksum verification fails the play if the checksum file is missing or doesn't match
- Currently supports Linux glibc (Ubuntu/RHEL/Rocky) on x86_64 and aarch64
- RHEL/Rocky 8 support is deferred until Molecule Docker images are updated

---

## Docs

* [x] Updated `defaults/main.yml` with new variables and documentation
* [x] Added spec and plan documents in `docs/plans/2026-01-install-with-uv/`
