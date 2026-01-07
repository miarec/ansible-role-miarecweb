import os

import testinfra.utils.ansible_runner

testinfra_hosts = testinfra.utils.ansible_runner.AnsibleRunner(
    os.environ["MOLECULE_INVENTORY_FILE"]
).get_hosts("all")

uv_version = os.environ.get("UV_VERSION")
uv_install_dir = os.environ.get("UV_INSTALL_DIR", "/usr/local/bin")


def test_uv_binaries_installed(host):
    for binary in ("uv", "uvx"):
        f = host.file(f"{uv_install_dir}/{binary}")
        assert f.exists
        assert f.is_file
        assert f.user == "root"
        assert f.group == "root"
        assert f.mode & 0o111


def test_uv_reports_expected_version(host):
    result = host.run(f"{uv_install_dir}/uv --version")
    assert result.rc == 0, f"uv --version failed: {result.stderr}"
    assert uv_version in result.stdout

    result = host.run(f"{uv_install_dir}/uvx --version")
    assert result.rc == 0, f"uvx --version failed: {result.stderr}"
    assert uv_version in result.stdout
