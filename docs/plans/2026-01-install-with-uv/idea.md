# Install uv binaries

Extend this ansible role to install uv binaries from the official releases.

Normally, the uv binaries are installed via command:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

But we don't want to run remote scripts directly on our servers for security and reliability reasons.

We analyzed the install script and documented the key steps it is doing in [uv_install.md](./uv_install.md).

The script itself is downloaded from [here](https://astral.sh/uv/install.sh) and saved locally to [uv_install.sh](./uv_install.sh).

## Requirements

Define variables:

- `uv_version`: version of uv to install, e.g. `v0.12.3`
- `uv_install_dir`: directory to install uv binaries to, e.g. `/usr/local/bin`
- `uv_download_base_url`: base URL to download uv binaries from
- `miarecweb_install_uv`: set to `true` to install uv binaries (default is `true`)

## Tasks

- Check if uv is already installed and at the correct version
- Detect OS and architecture to determine the final download URL
- Download the uv tarball from the constructed URL
- Extract the uv binary from the tarball
- Install the uv binary to the specified directory
- Set appropriate permissions on the installed binary
- Clean-up temporary files after installation (if any)

All these tasks must be tagged with `uv` for easy isolation (will be used in molecule tests).

## Verification

- Check *.yml files with  ansible-lint
- Create molecule scenario to verify uv installation (use tag `uv` to run only uv installation tasks and ignore others from this role))
- Create the second molecule scenario to verify uv upgrade from an older version to the specified version

## Other notes

We should support the following OS/architectures:

OS:

- RedHat-like (rhel, rockylinux), 8+
- Ubuntu

Arch:

- x86_64
- aarch64
