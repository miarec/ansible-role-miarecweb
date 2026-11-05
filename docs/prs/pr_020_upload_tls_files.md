# 2026-10-04-upload-tls-files

Moves the TLS file upload into the role, so a renewed certificate restarts only the service that reads it.

## 🎯 Problem

The ansible-miarec playbooks deploy several services, often on one host, and upload the TLS files of each service with a shared task in `pre_tasks`. Each play then restarts its service from `post_tasks` when a variable registered by that task reports a change. Registered variables survive across plays, so one changed certificate restarts every service deployed later on the same host, including services that never read the file. The playbooks also depend on a variable name internal to the shared task file.

---

## 👀 What changes for users

Before, the role expected the TLS files to exist on the host and failed early when one was missing. After, setting `miarecweb_db_tls_*_src` and `miarecweb_redis_tls_*_src` makes the role copy the files from the Ansible control machine, set root ownership with mode 0644 for certificates and 0640 for private keys readable by `miarec_bin_group`, and reload Apache and restart Celery when a file changed. Leaving the variables empty, the default, keeps the previous behavior.

The Apache site config and the Celery environment files are now rendered with LF line endings. Their templates have carried CRLF endings since the first commit in 2017.

A deployment that runs the web application under a dedicated `mod_wsgi_user` now gets that user added to `miarec_bin_group`, instead of the Apache user, so it can read the uploaded keys and write to the recordings directory. A host that runs only the Celery scheduler gets its Celery user added to the group as well.

---

## 🐛 Bug details

* **Severity**: medium. Only deployments that set `mod_wsgi_user` to an account other than `apache_user` are affected, and the operator can add the user to the group by hand.
* **Symptom**: the web application cannot write to the recordings directory, and with this PR cannot read the TLS private keys, because the group grant went to the Apache user while the application runs as the mod_wsgi daemon user.
* **Exposure**: since commit `46c9d6c` (2024-07-12) introduced `mod_wsgi_user` without moving the group grant with it. The default keeps both users equal, which is why the test scenarios never caught it.

---

## 💥 Impact

* **Who is affected**: deployments that set the new `*_src` variables, starting with ansible-miarec. Every deployment sees the three template tasks report `changed` once on the next run, which reloads Apache and restarts Celery; later runs are idempotent again. Deployments with a dedicated `mod_wsgi_user` see that user join `miarec_bin_group` on the next run.
* **Who is not affected**: existing deployments, beyond that one-time restart. The `*_src` defaults are empty, so no new task runs. A scheduler-only host already had its Celery user in the group when the worker was installed on the same host, which is the common case.
* **Keys the role doesn't upload**: the role no longer changes the group or mode of a private key that is already on the host (set with `*_file` but no `*_src`). A key that the Apache or Celery user can't read fails the play with the user and file named. The TLS feature has not been deployed to production, so no deployment relied on the removed tasks.
* **Conditions**: `miarecweb_db_tls` or `miarecweb_redis_tls` enabled and at least one `*_src` variable set.

---

## 🔧 Implementation notes

* The role sets permissions only on the files it uploads, never on directories or on files that are already on the host. A missing parent directory is created as `0755 root:root`, regardless of the host's umask, and an existing one is left alone, so a file in a shared directory such as `/etc/ssl/certs` or `/etc/ssl/private` doesn't change that directory's permissions. The two pre-existing tasks that set the group and mode on the key file and its directory are removed for the same reason.
* Before the release is finalized, the role checks that the mod_wsgi and Celery users can read every TLS file in use, uploaded or not. A key they cannot open fails the play with the previous release still active, instead of failing the service at its next restart. The check runs after the database migration, because the Celery user is created with the Celery services; moving it earlier would mean reshuffling user management across three task files, and the loud failure is considered enough.
* The check runs as the users through `runuser`, which applies their supplementary groups the way mod_wsgi and systemd do, so it also proves the group membership. It is built from a few small tasks with a `when` each, rather than one Jinja expression, so the conditions read as Ansible.
* The preflight check that required a non-root `miarecweb_celery_user` for client certificates now also requires a non-root `miarec_bin_group`, because the role writes the uploaded key as `root:{{ miarec_bin_group }}` with mode 0640. Its message already asked for both.
* The preflight checks that verified the TLS files already existed on the host are removed. They dated from the first TLS commit, when the playbook uploaded the files, and a missing file now fails either in the copy task, which names the missing source, or in the verify step.
* The TLS Molecule scenario generates the certificates on the control machine. The PostgreSQL and Redis fixtures upload their own server certificates, and nothing in prepare writes to `/etc/miarecweb/tls`, so a passing test proves that the role creates the directory and uploads the client files. The CA private key never reaches the target, and verify asserts that. The scenario runs Celery as a non-root user, so it also proves the group-based access to the keys.
* `.gitattributes` normalizes line endings to LF, so a Windows checkout can't reintroduce CRLF. `.yamllint` mirrors the rules that `.ansible-lint` skips and allows spaces inside braces.
