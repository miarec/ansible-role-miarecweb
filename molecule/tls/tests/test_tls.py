import json
import os
import testinfra.utils.ansible_runner

testinfra_hosts = testinfra.utils.ansible_runner.AnsibleRunner(
    os.environ['MOLECULE_INVENTORY_FILE']).get_hosts('all')

miarecweb_version = os.environ.get('MIARECWEB_VERSION')

# PostgreSQL and Redis each have their own PKI. The role uploads the client
# files into a directory per service.
SERVICES = ("postgresql", "redis")


def test_tls_certificates_exist(host):
    """Verify TLS certificates were uploaded."""
    cert_files = [
        # CA and client certs per service, uploaded by the role
        *(f"/etc/miarecweb/tls/{svc}/{name}"
          for svc in SERVICES for name in ("ca.crt", "client.crt", "client.key")),
        # PostgreSQL server certs in /etc/postgresql/tls/, uploaded by prepare
        "/etc/postgresql/tls/server.crt",
        "/etc/postgresql/tls/server.key",
        "/etc/postgresql/tls/ca.crt",
        # Redis server certs in /etc/redis/tls/, uploaded by prepare
        "/etc/redis/tls/server.crt",
        "/etc/redis/tls/server.key",
        "/etc/redis/tls/ca.crt",
    ]
    for cert_file in cert_files:
        f = host.file(cert_file)
        assert f.exists, f"Certificate file not found: {cert_file}"
        assert f.is_file, f"Not a file: {cert_file}"


def test_ca_key_not_on_host(host):
    """The CA private keys stay on the control machine."""
    for svc in SERVICES:
        assert not host.file(f"/etc/miarecweb/tls/{svc}/ca.key").exists


def test_tls_file_permissions(host):
    """The role uploads the private keys readable by the service group only."""
    for svc in SERVICES:
        key = host.file(f"/etc/miarecweb/tls/{svc}/client.key")
        assert key.user == "root", f"{svc} key is not owned by root"
        assert key.group == "miarec", f"{svc} key is not group miarec"
        assert key.mode == 0o640, f"{svc} key is not 0640"
        for name in ("ca.crt", "client.crt"):
            cert = host.file(f"/etc/miarecweb/tls/{svc}/{name}")
            assert cert.user == "root", f"{svc}/{name} is not owned by root"
            assert cert.mode == 0o644, f"{svc}/{name} is not 0644"
        # The role created the directory, so it has the fixed mode, not the umask.
        tls_dir = host.file(f"/etc/miarecweb/tls/{svc}")
        assert tls_dir.user == "root", f"{svc} directory is not owned by root"
        assert tls_dir.mode == 0o755, f"{svc} directory is not 0755"


def test_production_ini_db_ssl_params(host):
    """Verify DATABASE_SSL_PARAMS is configured in production.ini."""
    ini_file = host.file(
        f"/opt/miarecweb/releases/{miarecweb_version}/production.ini"
    )
    assert ini_file.exists, "production.ini not found"

    content = ini_file.content_string
    assert "DATABASE_SSL_PARAMS" in content, "DATABASE_SSL_PARAMS not found in production.ini"
    assert "sslmode=verify-ca" in content, "sslmode not configured correctly"
    assert "sslrootcert=/etc/miarecweb/tls/postgresql/ca.crt" in content, "sslrootcert not configured"
    assert "sslcert=/etc/miarecweb/tls/postgresql/client.crt" in content, "sslcert not configured"
    assert "sslkey=/etc/miarecweb/tls/postgresql/client.key" in content, "sslkey not configured"


def test_production_ini_redis_ssl_params(host):
    """Verify Redis TLS settings are configured in production.ini."""
    ini_file = host.file(
        f"/opt/miarecweb/releases/{miarecweb_version}/production.ini"
    )
    assert ini_file.exists, "production.ini not found"

    content = ini_file.content_string
    assert "REDIS_SCHEMA" in content, "REDIS_SCHEMA not found in production.ini"
    assert "rediss" in content, "Redis TLS schema (rediss) not configured"
    assert "REDIS_SSL_PARAMS" in content, "REDIS_SSL_PARAMS not found in production.ini"
    assert "ssl_ca_certs=/etc/miarecweb/tls/redis/ca.crt" in content, "ssl_ca_certs not configured"
    assert "ssl_certfile=/etc/miarecweb/tls/redis/client.crt" in content, "ssl_certfile not configured"
    assert "ssl_keyfile=/etc/miarecweb/tls/redis/client.key" in content, "ssl_keyfile not configured"


def test_postgresql_ssl_enabled(host):
    """Verify PostgreSQL has SSL enabled."""
    result = host.run(
        "sudo -u postgres psql -tAc \"SHOW ssl;\""
    )
    assert result.rc == 0, f"Failed to query PostgreSQL: {result.stderr}"
    assert "on" in result.stdout, "PostgreSQL SSL is not enabled"


def test_redis_tls_listening(host):
    """Verify Redis is listening on TLS port."""
    socket = host.socket("tcp://127.0.0.1:6379")
    assert socket.is_listening, "Redis is not listening on TLS port 6379"


def test_directories(host):
    """Verify required directories exist."""
    dirs = [
        f"/opt/miarecweb/releases/{miarecweb_version}",
        "/var/log/miarecweb",
        "/var/log/miarecweb/celery"
    ]
    for dir_path in dirs:
        d = host.file(dir_path)
        assert d.is_directory, f"Directory not found: {dir_path}"
        assert d.exists, f"Directory does not exist: {dir_path}"


def test_files(host):
    """Verify required files exist."""
    files = [
        f"/opt/miarecweb/releases/{miarecweb_version}/production.ini",
        "/etc/systemd/system/celerybeat.service",
        "/etc/systemd/system/celeryd.service",
    ]
    for file_path in files:
        f = host.file(file_path)
        assert f.exists, f"File not found: {file_path}"
        assert f.is_file, f"Not a file: {file_path}"


def test_services(host):
    """Verify services are enabled and running."""
    if host.system_info.distribution == "ubuntu":
        services = ["apache2", "celeryd", "celerybeat"]
    else:
        services = ["httpd", "celeryd", "celerybeat"]

    for service in services:
        s = host.service(service)
        assert s.is_enabled, f"Service {service} is not enabled"
        assert s.is_running, f"Service {service} is not running"


def test_celery_runs_as_celery_user(host):
    """The worker runs as the non-root celery user, a member of miarec_bin_group."""
    assert "miarec" in host.user("celery").groups
    workers = [p for p in host.process.filter(user="celery") if "celery" in p.comm]
    assert workers, "No celery process runs as user celery"
    root_workers = [p for p in host.process.filter(user="root") if "celery" in p.comm]
    assert not root_workers, "A celery process runs as root"


def test_celery_user_can_read_tls_keys(host):
    """The celery user reads the private keys through miarec_bin_group."""
    for svc in SERVICES:
        result = host.run(f"runuser -u celery -- cat /etc/miarecweb/tls/{svc}/client.key")
        assert result.rc == 0, f"celery cannot read {svc} client.key: {result.stderr}"


def test_celery_worker_reachable_over_redis_tls(host):
    """A ping from the celery user reaches the worker through Redis over TLS."""
    result = host.run(
        "runuser -u celery -- /opt/miarecweb/current/pyenv/bin/celery "
        "-A miarecweb.celery_app inspect ping "
        "--ini-file=/opt/miarecweb/current/production.ini --timeout 30"
    )
    assert result.rc == 0, f"celery inspect ping failed: {result.stderr}"
    assert "pong" in result.stdout, f"Worker did not answer the ping: {result.stdout}"


def test_health_endpoint(host):
    """Verify /health endpoint returns healthy status for dependencies."""
    result = host.run("curl -sSLk -w '\\n%{http_code}' http://localhost/health")
    assert result.rc == 0, f"Health endpoint curl failed (rc={result.rc}): {result.stderr}"

    output_lines = result.stdout.splitlines()
    assert output_lines, "Health endpoint returned no output"

    status_line = output_lines[-1]
    body = "\n".join(output_lines[:-1])

    try:
        http_status = int(status_line)
    except ValueError as exc:
        raise AssertionError(
            f"Could not parse HTTP status from health response: {status_line}\n"
            f"Full response:\n{result.stdout}\nStderr:\n{result.stderr}"
        ) from exc

    if http_status != 200:
        raise AssertionError(
            f"Health endpoint returned HTTP {http_status}\n"
            f"Body:\n{body or '<empty>'}\nStderr:\n{result.stderr}"
        )

    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        raise AssertionError(
            f"Health endpoint response is not valid JSON: {exc}\nResponse: {body}"
        )

    assert payload.get("status") == "ok", f"Unexpected overall status: {payload}"
    assert payload.get("postgresql") == "ok", f"Unexpected PostgreSQL status: {payload}"
    assert payload.get("redis") == "ok", f"Unexpected Redis status: {payload}"


def test_alembic_with_tls(host):
    """Verify alembic can connect to PostgreSQL with TLS (via environment variables)."""
    # This works because upgrade_db.yml passes PGSSLMODE/PGSSLCERT/PGSSLKEY
    # as environment variables to alembic commands
    result = host.run(
        "PGSSLMODE=verify-ca "
        "PGSSLCERT=/etc/miarecweb/tls/postgresql/client.crt "
        "PGSSLKEY=/etc/miarecweb/tls/postgresql/client.key "
        "PGSSLROOTCERT=/etc/miarecweb/tls/postgresql/ca.crt "
        "/opt/miarecweb/current/pyenv/bin/alembic -c /opt/miarecweb/current/production.ini current"
    )
    assert result.rc == 0, f"Alembic failed to connect with TLS: {result.stderr}"
    assert "(head)" in result.stdout or "head" in result.stdout.lower(), \
        f"Database not at head revision: {result.stdout}"
