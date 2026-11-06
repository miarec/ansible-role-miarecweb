# 2026-11-05-cache-dir-mod-wsgi-user

Fixes a high-severity, low-likelihood bug where the web portal fails on every page when the mod_wsgi daemon runs as a user other than the Apache user.

## 🎯 Problem

An operator who sets `mod_wsgi_user` to a dedicated account, which PR 20 made the supported way to give the web application access to the TLS private keys, gets a web portal that returns a server error on every page. The web application compiles its page templates into a cache directory inside the release at runtime, and that directory belonged to the Apache user with group read-only, so the daemon user could not write to it.

---

## 👀 What changes for users

With the default settings nothing changes: `mod_wsgi_user` is the Apache user, and the cache directory keeps the same owner. With a dedicated `mod_wsgi_user`, the web portal now renders pages, because the cache directory belongs to that user and its group.

---

## 🐛 Bug details

* **Severity**: high for the affected configuration, with no workaround short of changing the directory by hand after every deploy. Low likelihood: the default configuration never hits it.
* **Symptom**: every page of the web portal returns an internal server error, and the Apache error log shows a permission error while writing a compiled template under `releases/<version>/cache`.
* **Exposure**: since `mod_wsgi_user` became configurable in 46c9d6c on 2024-07-12. The cache task has created the directory for the Apache user since the first commit of the role.

---

## 💥 Impact

* **Who is affected**: deployments that set `mod_wsgi_user` or `mod_wsgi_group` to something other than the Apache user and group.
* **Who is not affected**: every deployment with the defaults, including all ansible-miarec playbooks, which don't set these variables.
* **Conditions**: `mod_wsgi_user` differs from `apache_user`.
