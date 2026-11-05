# 2026-10-04-upload-tls-files

Moves the TLS file upload into the role, so a renewed certificate restarts only the service that reads it.

## 🎯 Problem

The ansible-miarec playbooks deploy several services, often on one host, and upload the TLS files of each service with a shared task in `pre_tasks`. Each play then restarts its service from `post_tasks` when a variable registered by that task reports a change. Registered variables survive across plays, so one changed certificate restarts every service deployed later on the same host, including services that never read the file. The playbooks also depend on a variable name internal to the shared task file.

---

## 👀 What changes for users

Before, the role expected the TLS files to exist on the host and failed early when one was missing. After, setting `miarecweb_db_tls_*_src` and `miarecweb_redis_tls_*_src` makes the role copy the files from the Ansible control machine, set root ownership with mode 0644 for certificates and 0640 for private keys readable by `miarec_bin_group`, and reload Apache and restart Celery when a file changed. Leaving the variables empty, the default, keeps the previous behavior.

The Apache site config and the Celery environment files are now rendered with LF line endings. Their templates have carried CRLF endings since the first commit in 2017.

---

## 💥 Impact

* **Who is affected**: deployments that set the new `*_src` variables, starting with ansible-miarec. Every deployment sees the three template tasks report `changed` once on the next run, which reloads Apache and restarts Celery; later runs are idempotent again.
* **Who is not affected**: existing deployments, beyond that one-time restart. The `*_src` defaults are empty, so no new task runs.
* **Keys the role doesn't upload**: the role no longer changes the group or mode of a private key that is already on the host (set with `*_file` but no `*_src`). A key that the Apache or Celery user can't read fails the play with the user and file named. The TLS feature has not been deployed to production, so no deployment relied on the removed tasks.
* **Conditions**: `miarecweb_db_tls` or `miarecweb_redis_tls` enabled and at least one `*_src` variable set.

---

## 🔧 Implementation notes

* The role sets permissions only on the files it uploads, never on directories or on files that are already on the host. A missing parent directory is created as `0755 root:root`, regardless of the host's umask, and an existing one is left alone, so a file in a shared directory such as `/etc/ssl/certs` or `/etc/ssl/private` doesn't change that directory's permissions. The two pre-existing tasks that set the group and mode on the key file and its directory are removed for the same reason.
* Before the release is finalized, the role checks that the Apache and Celery users can read every TLS file in use, uploaded or not. A key they cannot open fails the play with the previous release still active, instead of failing the service at its next restart.
* The preflight check that required a non-root `miarecweb_celery_user` for client certificates now also requires a non-root `miarec_bin_group`, because the role writes the uploaded key as `root:{{ miarec_bin_group }}` with mode 0640. Its message already asked for both.
* The preflight check skips a file that has a `*_src` variable, because the copy task reports a missing source. Files without one are still checked on the host.
* The TLS Molecule scenario generates the certificates on the control machine. The PostgreSQL and Redis fixtures upload their own server certificates, and nothing in prepare writes to `/etc/miarecweb/tls`, so a passing test proves that the role creates the directory and uploads the client files. The CA private key never reaches the target, and verify asserts that.
* `.gitattributes` normalizes line endings to LF, so a Windows checkout can't reintroduce CRLF. `.yamllint` mirrors the rules that `.ansible-lint` skips and allows spaces inside braces.
