# 2026-11-08-celery-probe-hosts

Adds a role variable so a monitoring service can use the Celery health probe of MiaRec Web, which the role offered no clean way to open to other hosts.

## 🎯 Problem

Since v2026.8.24, MiaRec Web has a Celery health probe at `/health/celery/probe`. It sends a task to a Celery worker and reports whether a worker ran it, which is the only check that proves background jobs work end to end. MiaRec Web answers the probe only for the addresses listed in its configuration, and the default lists only the web server itself. So an external monitoring service, which is where operators need the probe, got HTTP 403.

---

## 👀 What changes for users

Operators can list the monitoring hosts or networks in `miarecweb_celery_probe_hosts`, and those hosts can call the probe. An empty list turns the probe off. By default, the probe answers only the web server itself, as before.

---

## 💥 Impact

* **Who is affected**: deployments of MiaRec Web v2026.8.24 or later that want to monitor Celery from another host.
* **Who is not affected**: deployments that don't set the variable, because the default matches the MiaRec Web default. Releases before v2026.8.24 have no probe, and the role leaves their configuration unchanged.
* **Conditions**: the variable takes effect on the next run of the role, which reloads Apache when the list changes.

---

## 🔧 Implementation notes

* The MiaRec Web sample configuration lists the default hosts on indented continuation lines. Neither `miarecweb_custom_ini_settings` (the `ini_file` module) nor `lineinfile` removes those lines, so the default hosts would remain in the list. The role therefore replaces the option together with its continuation lines.
* The role's own Molecule scenarios install MiaRec Web v2026.1.11, which predates the probe. The ansible-miarec test suite calls the probe from allowed and other hosts.
