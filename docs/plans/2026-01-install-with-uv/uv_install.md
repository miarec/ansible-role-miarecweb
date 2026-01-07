# UV Installation Reference

## Download URL Format

Base URL pattern:
```
https://github.com/astral-sh/uv/releases/download/{VERSION}/uv-{ARCH}.tar.gz
```

Example:
```
https://github.com/astral-sh/uv/releases/download/0.9.22/uv-x86_64-unknown-linux-gnu.tar.gz
```

## Available Archives

| OS | CPU | Archive Name |
|----|-----|--------------|
| Linux (glibc) | x86_64 | `uv-x86_64-unknown-linux-gnu.tar.gz` |
| Linux (glibc) | aarch64 | `uv-aarch64-unknown-linux-gnu.tar.gz` |
| Linux (glibc) | i686 | `uv-i686-unknown-linux-gnu.tar.gz` |
| Linux (glibc) | armv7 | `uv-armv7-unknown-linux-gnueabihf.tar.gz` |
| Linux (musl) | x86_64 | `uv-x86_64-unknown-linux-musl.tar.gz` |
| Linux (musl) | aarch64 | `uv-aarch64-unknown-linux-musl.tar.gz` |
| Linux (musl) | i686 | `uv-i686-unknown-linux-musl.tar.gz` |
| Linux (musl) | armv7 | `uv-armv7-unknown-linux-musleabihf.tar.gz` |
| Linux (musl) | arm | `uv-arm-unknown-linux-musleabihf.tar.gz` |
| Linux (glibc) | ppc64 | `uv-powerpc64-unknown-linux-gnu.tar.gz` |
| Linux (glibc) | ppc64le | `uv-powerpc64le-unknown-linux-gnu.tar.gz` |
| Linux (glibc) | s390x | `uv-s390x-unknown-linux-gnu.tar.gz` |
| Linux (glibc) | riscv64 | `uv-riscv64gc-unknown-linux-gnu.tar.gz` |
| macOS | x86_64 | `uv-x86_64-apple-darwin.tar.gz` |
| macOS | arm64 | `uv-aarch64-apple-darwin.tar.gz` |
| Windows | x86_64 | `uv-x86_64-pc-windows-msvc.zip` |
| Windows | i686 | `uv-i686-pc-windows-msvc.zip` |
| Windows | aarch64 | `uv-aarch64-pc-windows-msvc.zip` |

## Architecture Detection

### OS Detection
- `uname -s` returns: `Linux`, `Darwin`, `FreeBSD`, `MINGW*`, `MSYS*`, `CYGWIN*`, `Windows_NT`

### CPU Detection
- `uname -m` returns: `x86_64`, `aarch64`, `arm64`, `armv7l`, `armv8l`, `i686`, `i386`, etc.
- macOS arm64 maps to `aarch64` in archive names

### Libc Detection (Linux only)
- **glibc**: Default for most Linux distributions
- **musl**: Alpine Linux and other musl-based distros

Detection method:
```
ldd --version 2>&1 | grep -q 'musl'
```
- If matches: musl
- Otherwise: glibc (gnu)

### glibc Version Requirements
The installer checks minimum glibc versions:
- x86_64-unknown-linux-gnu: glibc >= 2.17
- aarch64-unknown-linux-gnu: glibc >= 2.28
- i686-unknown-linux-gnu: glibc >= 2.17
- armv7-unknown-linux-gnueabihf: glibc >= 2.17

If glibc is too old, installer falls back to musl static binary.

## Archive Contents

The tar.gz archive contains a single directory named `uv-{ARCH}/` with binaries inside:

```
uv-x86_64-unknown-linux-gnu/
uv-x86_64-unknown-linux-gnu/uv
uv-x86_64-unknown-linux-gnu/uvx
```

Binaries:
- `uv` - Main uv binary
- `uvx` - Tool runner (like pipx)

Windows archives also include:
- `uvw.exe` - Windows-specific variant

## Default Install Locations

The installer writes binaries to the first existing location (in order):

1. `$UV_INSTALL_DIR` (if set)
2. `$XDG_BIN_HOME` (if set)
3. `$XDG_DATA_HOME/../bin` (if XDG_DATA_HOME is set)
4. `$HOME/.local/bin` (default fallback)

For system-wide installation, common choices:
- `/usr/local/bin`
- `/opt/uv/bin`

## Environment Variables

| Variable | Description |
|----------|-------------|
| `UV_INSTALL_DIR` | Force install directory |
| `UV_NO_MODIFY_PATH` | Set to `1` to skip shell profile modifications |
| `UV_UNMANAGED_INSTALL` | Install path without PATH mods or updater receipt |
| `UV_DOWNLOAD_URL` | Custom base URL for downloading archives |
| `UV_GITHUB_TOKEN` | Auth token for GitHub Enterprise or private repos |
