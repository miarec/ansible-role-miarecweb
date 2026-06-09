import json
import os
import testinfra.utils.ansible_runner

testinfra_hosts = testinfra.utils.ansible_runner.AnsibleRunner(
    os.environ['MOLECULE_INVENTORY_FILE']).get_hosts('all')

miarecweb_version = os.environ.get('MIARECWEB_VERSION')


def test_upgraded_release(host):
    # The new (upgraded) version is installed and active.
    release_dir = host.file("/opt/miarecweb/releases/{}".format(miarecweb_version))
    assert release_dir.exists
    assert release_dir.is_directory

    current = host.file("/opt/miarecweb/current")
    assert current.is_symlink
    assert current.linked_to == "/opt/miarecweb/releases/{}".format(miarecweb_version)


def test_services_running_after_upgrade(host):
    # The stop_*_on_alembic_upgrade tasks stop the services before the database
    # upgrade; the handlers must start them again afterwards.
    if host.system_info.distribution == "ubuntu":
        services = ["celeryd", "celerybeat", "apache2"]
    else:
        services = ["celeryd", "celerybeat", "httpd"]

    for service in services:
        s = host.service(service)
        assert s.is_enabled
        assert s.is_running


def test_database_at_head(host):
    # After the upgrade the alembic revision must be at head.
    result = host.run(
        "/opt/miarecweb/current/pyenv/bin/alembic "
        "-c /opt/miarecweb/current/production.ini current"
    )
    assert result.rc == 0, f"alembic current failed: {result.stderr}"
    assert "(head)" in result.stdout, f"Database is not at head: {result.stdout}"


def test_health_endpoint(host):
    result = host.run("curl -fsSLk http://localhost/health")
    assert result.rc == 0, f"Health endpoint not reachable: {result.stderr}"

    payload = json.loads(result.stdout)
    assert payload.get("status") == "ok", f"Unexpected overall status: {payload}"
    assert payload.get("postgresql") == "ok", f"Unexpected PostgreSQL status: {payload}"
    assert payload.get("redis") == "ok", f"Unexpected Redis status: {payload}"
