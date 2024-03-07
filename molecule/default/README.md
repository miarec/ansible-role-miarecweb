# Molecule test this role

Run Molecule test
```
molecule test
```

Run test with variable example
```
MOLECULE_DISTRO=centos7 MOLECULE_MIARECWEB_VERSION=8.0.0.3909 molecule test
```

## Variables
 - `MOLECULE_DISTRO` OS of docker container to test, default `ubuntu2204`
    List of tested distros
    - `ubuntu2204`
    - `ubuntu2004`
    - `centos7`
 - `MOLECULE_MIARECWEB_VERSION` defines variable `miarecweb_version`, default `2024.1.1.0`
 - `MOLECULE_MIARECWEB_SECRET` defines variabled `miarecweb_secret`, default `secret`
 - `MOLECULE_ANSIBLE_VERBOSITY` set verbosity for ansible run, like running "ansible -vvv", values 0-3, default 0