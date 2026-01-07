import os

import testinfra.utils.ansible_runner

testinfra_hosts = testinfra.utils.ansible_runner.AnsibleRunner(
    os.environ["MOLECULE_INVENTORY_FILE"]
).get_hosts("all")

uv_old_version = os.environ.get("UV_OLD_VERSION")
uv_version = os.environ.get("UV_VERSION")
uv_install_dir = os.environ.get("UV_INSTALL_DIR", "/usr/local/bin")


def test_scenario_versions_are_different():
    assert uv_old_version
    assert uv_version
    assert uv_old_version != uv_version


def test_uv_reports_expected_version(host):
    result = host.run(f"{uv_install_dir}/uv --version")
    assert result.rc == 0, f"uv --version failed: {result.stderr}"
    assert uv_version in result.stdout
    assert uv_old_version not in result.stdout

    result = host.run(f"{uv_install_dir}/uvx --version")
    assert result.rc == 0, f"uvx --version failed: {result.stderr}"
    assert uv_version in result.stdout
    assert uv_old_version not in result.stdout

