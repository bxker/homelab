# Spec: Pin the k3s version and keep the join token off command lines

Ticket: gh:16 · Size: standard · Status: approved

## Problem
Every k3s install pulls whatever version `get.k3s.io` serves that day, so a node replaced next month
can join on a different version than the rest, and rebuilds aren't reproducible. Workers also receive the
cluster join token as an inline environment variable in a shell command, which shows up in the process
list and in Ansible's verbose output. Anyone holding the token can join a node to the cluster.

## Goals
- One version variable decides what every node installs, and Renovate proposes bumps to it.
- The join token never appears in a command line, an env var on a command, or Ansible output.

## Non-goals
- Upgrading existing nodes (system-upgrade-controller, later phase). Disabling bundled components (#12).

## Acceptance criteria
- **AC1**: Given the playbook, then the server and agent installs both set `INSTALL_K3S_VERSION` from one
  variable `k3s_version` defined once in `ansible/inventory.yml`.
- **AC2**: Given the playbook, then the install script itself is fetched from the same pinned tag
  (`raw.githubusercontent.com/k3s-io/k3s/<k3s_version>/install.sh`), not `get.k3s.io`.
- **AC3**: Given the playbook, then no task puts the token on a command line or in a command's environment;
  agents read `server`/`token` from `/etc/rancher/k3s/config.yaml` (root, `0600`), and every task that
  handles the token is `no_log: true`.
- **AC4**: Given nodes that already run k3s, when the playbook re-runs, then it doesn't reinstall or restart
  k3s (installs stay guarded by `creates:`).
- **AC5**: Given `renovate.json`, then a custom manager matches the `k3s_version` line and looks it up
  against `k3s-io/k3s` GitHub releases (regex checked offline against the inventory line).

- **AC6**: Given a node that already runs k3s at a version other than `k3s_version`, when the playbook
  runs, then it fails before changing anything on any node and prints the live and pinned versions.

## Constraints
- `install.sh` (checked at v1.34.12+k3s1) installs an agent when given the `agent` command, with
  `server`/`token` taken from `config.yaml`, so no `K3S_URL`/`K3S_TOKEN` is needed.
- The pinned version must equal what the cluster runs now, or a newly installed node would skew from the
  rest (OQ1).

## Requirement changes
None.

## Open questions
None. Resolved at the Spec gate:
1. The live version is unknown: Terraform only creates the VMs, and k3s came from whatever `get.k3s.io`
   served at install time. Pin `v1.36.5+k3s1` provisionally and add AC6 so a mismatch fails loudly instead
   of skewing; the owner corrects the pin from the printed live version.
2. Run `ansible-playbook --syntax-check` and `ansible-lint` ephemerally via `uvx`.
