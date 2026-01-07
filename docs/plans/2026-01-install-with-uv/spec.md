# Install `uv` Binaries (Official Releases) — Specification

## 1. Context & Goals (User/Business Perspective)
- Extend `ansible-role-miarecweb` to optionally install `uv` binaries from official GitHub releases (not via remote installer scripts).
- Primary users: operators running this role in production and CI/Molecule where `uv` is required/desired.
- Goals (success looks like):
  - `uv` and `uvx` are installed (or upgraded) deterministically when enabled.
  - Installation is idempotent and version-aware (no changes when the requested version is already present).
  - Download integrity is verified by default using GitHub-hosted per-archive SHA256 checksum assets.

## 2. Non-Goals / Out of Scope
- Do not switch MiaRecWeb’s app/dependency installation from `pip` to `uv` in this effort (explicitly deferred).
- Do not execute remote install scripts (no `curl ... | sh` patterns).
- Do not modify user shell profiles or PATH; installation location is controlled by role variables only.
- Platform scope:
  - In scope: Ubuntu 22.04/24.04; RedHat-family Linux including RHEL 9 and Rocky Linux 9+.
  - Deferred: RHEL/Rocky 8 support (until Molecule Docker images are updated to include a sufficiently new Python for the Ansible version used).
- Do not support non-Linux platforms (macOS/Windows) or Alpine/musl variants.

## 3. Definitions / Glossary
- `uv`: Python package manager CLI distributed as a prebuilt binary.
- `uvx`: companion tool runner binary distributed alongside `uv`.
- “Archive”: `uv-<arch>.tar.gz` GitHub release asset containing `uv` and `uvx`.
- “Checksum file”: per-archive `uv-<arch>.tar.gz.sha256` asset used for integrity verification.

## 4. Functional Requirements
### 4.1 User stories
- As an operator, I can enable/disable `uv` installation via `miarecweb_install_uv` (default: `true`) so I can opt out when `uv` is managed elsewhere.
- As an operator, I can pin `uv_version` (format: `0.12.3`, no leading `v`) so installs are reproducible.
- As an operator, I can control where binaries are installed via `uv_install_dir` (default: `/usr/local/bin`) so they land on the expected PATH.
- As an operator, I can override the download source via `uv_download_base_url` (default: `https://github.com/astral-sh/uv/releases/download`) for mirrors or restricted environments.
- As a test/CI user, I can run only the uv-related tasks using Ansible tag `uv`.

### 4.2 Use cases (happy path + key variants)
- UC1: Fresh install — when `miarecweb_install_uv: true`, install both `uv` and `uvx` into `uv_install_dir`; they are runnable after the role completes.
- UC2: No-op — if `uv`/`uvx` are already present at the requested `uv_version`, uv-related tasks make no changes.
- UC3: Upgrade — if an older version is present, upgrade to `uv_version`; a subsequent run is idempotent.
- UC4: Integrity verification — when `uv_verify_checksum: true` (default), validate the downloaded archive using `uv-<arch>.tar.gz.sha256` from the same GitHub release. If the checksum file cannot be downloaded or validation fails, the role fails the play.

### 4.3 Edge cases & failure modes
- Unsupported OS/CPU architecture: fail with a clear, actionable error.
- Unwritable/missing `uv_install_dir`: fail with a clear, actionable error.
- Missing release assets (archive or checksum): fail with a clear, actionable error.
- Temporary artifacts created during install/upgrade should be cleaned up on success and, where feasible, on failure.

## 5. Non-Functional Requirements
- Security:
  - Must not execute any remote scripts.
  - When `uv_verify_checksum: true` (default), must verify the downloaded archive using the matching GitHub-hosted per-archive checksum asset.
  - If checksum download fails or validation fails, must fail the play.
- Reliability/Idempotence:
  - Re-running with the same inputs results in no changes when `uv`/`uvx` already match `uv_version`.
  - Upgrade behavior is deterministic (requested version always wins).
- Operational clarity:
  - Failures are actionable with clear messages (unsupported OS/arch, missing assets, permission/FS issues).

## 6. UX / API Contracts (as applicable)
- New/updated variables:
  - `miarecweb_install_uv` (`true` by default)
  - `uv_version` (e.g. `0.12.3`)
  - `uv_install_dir` (`/usr/local/bin` by default)
  - `uv_download_base_url` (`https://github.com/astral-sh/uv/releases/download` by default)
  - `uv_verify_checksum` (`true` by default)
- Task tagging:
  - All uv-related tasks are tagged `uv`.
- Installed binaries:
  - On Linux, install `uv` and `uvx` (not `uvw.exe`).

## 7. Data & State
- Installed artifacts:
  - `uv` and `uvx` present in `uv_install_dir` with executable permissions and root ownership (system-wide install intent).
- No persistent receipts or shell modifications are required by this feature.
- No changes to MiaRecWeb release/app directories are part of uv installation scope.

## 8. Acceptance Criteria (Top-level)
- When `miarecweb_install_uv: true`, `uv` and `uvx` are installed in `uv_install_dir` and runnable (`uv --version`, `uvx --version`) on:
  - Ubuntu 22.04 and 24.04
  - RHEL-family Linux including RHEL 9 and Rocky Linux 9+
  - CPU: `x86_64` and `aarch64`
- When `uv_version` is already installed, uv-related tasks are idempotent (no changes on re-run).
- When an older version is installed, the role upgrades to `uv_version`; a subsequent run is idempotent.
- When `uv_verify_checksum: true` (default), installation fails if:
  - `uv-<arch>.tar.gz.sha256` cannot be downloaded, or
  - checksum validation fails.
- All uv-related tasks are runnable in isolation via tag selection.
- Repo verification expectations for this change:
  - `uv run ansible-lint` passes for any added/modified YAML.
  - Molecule coverage exists for:
    - uv install (running only `uv` tag / isolating uv tasks from the rest of the role)
    - uv upgrade (starting from an older version → requested `uv_version`)

## 9. Open Questions
- None (decisions captured: install `uv`+`uvx`, `uv_version` format, defaults, checksum behavior, OS scope incl. Rocky 9+, RHEL/Rocky 8 deferred).

## 10. Assumptions
- GitHub release assets for `uv` include:
  - `uv-<arch>.tar.gz` and the matching `uv-<arch>.tar.gz.sha256` for the requested `uv_version`.
- Molecule Docker images used for EL 8 will be upgraded later to satisfy Ansible’s Python minimum requirement before adding EL 8 coverage.

## 11. References
- Requirements source: `docs/plans/2026-01-install-with-uv/idea.md`
- Astral uv install script (explicitly not executed by this role): https://astral.sh/uv/install.sh
- GitHub release URL pattern (archives): https://github.com/astral-sh/uv/releases/download/{VERSION}/uv-{ARCH}.tar.gz
- Example archive URL: https://github.com/astral-sh/uv/releases/download/0.9.22/uv-x86_64-unknown-linux-gnu.tar.gz
- Archive naming/architecture notes: `docs/plans/2026-01-install-with-uv/uv_install.md`
- Local copy of analyzed installer script (for reference only): `docs/plans/2026-01-install-with-uv/uv-installer.sh`
