# Pull Request Description Template

## Summary

Add CI testing support for EL8 distributions (RHEL 8 and Rocky Linux 8) by pinning Ansible to version 9.x (ansible-core 2.16), which is the last version supporting Python 3.6 on managed nodes.

---

## Purpose

EL8 distributions ship with Python 3.6 as the system Python. The `dnf` Ansible module requires `python3-dnf` bindings, which are only available for the system Python interpreter. Since ansible-core 2.17+ requires Python 3.7+ on managed nodes, we must pin to ansible-core 2.16 to maintain EL8 compatibility.

This allows the role to be tested against all currently supported RHEL-family distributions.

---

## Testing

How did you verify it works?

* [x] Added/updated tests - Added rockylinux8 and rhel8 to CI matrix
* [x] Ran `ansible-lint` - Passed with 0 failures, 0 warnings

Notes:
- CI will run molecule tests on rockylinux8 and rhel8 after merge
- Ansible version pin allows all distros (including EL8) to use the same test command

---

## Related Issues

N/A - Proactive support expansion for EL8 distributions

---

## Changes

Brief list of main changes:

* Pin Ansible to `>=9.0,<10.0` in `pyproject.toml` to use ansible-core 2.16
* Add `rockylinux8` and `rhel8` to CI test matrix in `.github/workflows/ci.yml`
* Add comprehensive documentation in README explaining EL8 compatibility constraints
* Update CLAUDE.md with new distro list and Ansible version note
* Update `uv.lock` to reflect pinned Ansible version

---

## Notes for Reviewers

- RHEL 8 reaches end-of-life in 2029. Once EL8 support is dropped, the `<10.0` pin can be removed
- The `[WARNING]: Collection community.docker does not support Ansible version 2.16.15` message is expected and can be safely ignored (metadata validation only)
- All other distros continue to work with the same test commands

---

## Docs

* [x] Updated README.md with EL8 testing documentation
* [x] Updated CLAUDE.md with new distro list and Ansible version info
