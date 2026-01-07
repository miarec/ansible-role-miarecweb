# Plan — Install `uv`/`uvx` Binaries (Official Releases)

Last updated: 2026-01-07

## Scope
- Source of truth: `docs/plans/2026-01-install-with-uv/spec.md`
- Goal: extend this role to install/upgrade `uv` and `uvx` from official GitHub releases, with checksum verification enabled by default, and provide Molecule coverage for install + upgrade.

## Verification / Acceptance Criteria
- Verify install + idempotence on:
  - Ubuntu 22.04 (`MOLECULE_DISTRO=ubuntu2204`)
  - Ubuntu 24.04 (`MOLECULE_DISTRO=ubuntu2404`)
  - RockyLinux 9 (`MOLECULE_DISTRO=rockylinux9`)
  - RedHat 9 (`MOLECULE_DISTRO=rhel9`)
- For each distro, run both scenarios:
  - `MOLECULE_DISTRO=<distro> uv run molecule test -s uv`
  - `MOLECULE_DISTRO=<distro> uv run molecule test -s uv_upgrade`

## Phases & Tasks

### Phase 1 — Plan Setup
- [x] (2026-01-07) Create `plan.md`

### Phase 2 — Role Variables + Tasks
- [x] (2026-01-07) Add defaults for uv variables
- [x] (2026-01-07) Add `molecule/uv` scenario + failing tests (Red)
- [x] (2026-01-07) Add uv installation tasks (idempotent, version-aware, checksum verification) (Green)
- [x] (2026-01-07) Wire uv tasks into `tasks/main.yml` with tag support (`uv`)

### Phase 3 — Molecule: Upgrade Scenario
- [x] (2026-01-07) Add `molecule/uv_upgrade` scenario with a pre-installed older uv version
- [x] (2026-01-07) Add Testinfra tests verifying upgrade to the requested version + idempotence

### Phase 5 — Quality Gates
- [x] (2026-01-07) Run `uv run ansible-lint`
- [x] (2026-01-07) Run `uv run molecule test -s uv`
- [x] (2026-01-07) Run `uv run molecule test -s uv_upgrade`

### Phase 6 — Polish
- [x] (2026-01-07) Rename `_uv_target_triple` to `_uv_architecture`
- [x] (2026-01-07) Simplify version check (uv only)
- [x] (2026-01-07) Parse `uv --version` (Homebrew)

## Decision Log
- (2026-01-07) Install both `uv` and `uvx`.
- (2026-01-07) `uv_version` input format is `0.12.3` (no leading `v`).
- (2026-01-07) Defaults:
  - `uv_install_dir: /usr/local/bin`
  - `uv_download_base_url: https://github.com/astral-sh/uv/releases/download`
  - `uv_verify_checksum: true`
- (2026-01-07) If checksum asset download fails or checksum mismatches, fail the play.
- (2026-01-07) OS scope: Ubuntu 22.04/24.04 + RHEL/Rocky 9+ in-scope; EL8 deferred (until Docker/Molecule images meet Ansible Python minimum).

## Surprises & Discoveries
- (2026-01-07) No project-wide testing/style standards docs found at `docs/standards/testing.md` or `docs/standards/code_styleguide.md` / `docs/standards/code_quality.md`.
- (2026-01-07) `uv run ansible-lint` emitted a `ResourceWarning` but still passed with 0 failures/warnings.

## Progress Notes
- (2026-01-07) Added `molecule/uv` scenario and confirmed Red: `molecule/uv/tests/test_uv.py` fails because `uv` is not installed yet.
- (2026-01-07) Green confirmed: `uv run molecule test -s uv` passes (install + idempotence + Testinfra checks for `uv`/`uvx`).
- (2026-01-07) Added `molecule/uv_upgrade` and confirmed upgrade behavior + idempotence: `uv run molecule test -s uv_upgrade` passes.

## Outcomes & Retrospective
- TBD
