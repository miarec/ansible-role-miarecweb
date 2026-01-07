# Install miarecweb with UV

Migrate from pip to UV for installing miarecweb.

We recently migrated miarecweb package to UV, which is a lot faster than pip to intall packages in Python virtual environments.

Also, there was breaking change of removing requirements.txt files from the package, which was used in this ansible role to install dependencies.

A goal of this task is to update the ansible role to use UV for installing miarecweb and its dependencies.

## Notes

### Python version handling

- This role accepts `python_version` variable to specify which Python version to use.
- It also tries to auto-detect the installed Python version if `python_version` is not specified.
- After determining the Python version, pass it to `uv`, so it used the correct python version (via `--python VERSION` option).

### Python virtual environment dir

- Keep the same location for the python virtual environment as before (i.e. `/opt/miarecweb/releases/{{ miarecweb_version }}/pyenv`).
- Pass it to `uv venv` command via `--path` option.

### Installing miarecweb

- By design, we download `tar.gz` package and extract it into the destination folder `/opt/miarecweb/releases/{{ miarecweb_version }}/app`.
- After that, we used to call `pip install -e .` to install the package in editable mode.
- With `uv`, we can run `uv pip install -e .` (need to verify if we have to pass the venv path to this command)
