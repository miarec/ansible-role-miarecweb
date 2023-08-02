import os
import testinfra.utils.ansible_runner

testinfra_hosts = testinfra.utils.ansible_runner.AnsibleRunner(
    os.environ['MOLECULE_INVENTORY_FILE']).get_hosts('all')


def test_directories(host):

    dirs = [
        "/opt/miarecweb/releases/8.0.0.3911",
        "/var/log/miarecweb",
        "/var/log/miarecweb/celery"
    ]
    for dir in dirs:
        d = host.file(dir)
        assert d.is_directory
        assert d.exists

def test_files(host):
    files = [
        "/opt/miarecweb/releases/8.0.0.3911/production.ini",
        "/etc/systemd/system/celerybeat.service",
        "/etc/systemd/system/celeryd.service",
        "/var/log/miarecweb/celery/beat.log",
        "/var/log/miarecweb/celery/worker1.log"
    ]

    for file in files:
        f = host.file(file)
        assert f.exists
        assert f.is_file

def test_service(host):
    if host.system_info.distribution == "ubuntu":
        services = [
            "celeryd",
            "celerybeat",
            "apache2"
        ]
    if host.system_info.distribution == "centos":
        services = [
            "celeryd",
            "celerybeat",
            "httpd"
        ]

    for service in services:
        s = host.service(service)
        assert s.is_enabled
        assert s.is_running

def test_socket(host):
    sockets = [
        "tcp://0.0.0.0:80",
        "tcp://0.0.0.0:443"
    ]
    for socket in sockets:
        s = host.socket(socket)
        assert s.is_listening