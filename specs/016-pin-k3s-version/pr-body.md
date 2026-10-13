Pin k3s to one version and keep the join token off command lines

## Why
Every k3s install pulled whatever `get.k3s.io` served that day, so a replaced node could join on a different version and rebuilds weren't reproducible. Workers also got the cluster join token as an inline env var, visible in the process list and in Ansible's verbose output. Anyone with the token can join a node.

## What changed
- **`k3s_version`** in `ansible/inventory.yml` pins both installs. `install.sh` is fetched from the same tag (`raw.githubusercontent.com/k3s-io/k3s/<version>/install.sh`) and run as a file, with no `curl | sh`.
- **Version check:** a new first play compares installed k3s with `k3s_version` and stops, before changing anything on any node, if they differ.
- **Token:** workers read `server`/`token` from `/etc/rancher/k3s/config.yaml` (root, 0600). Every task that handles the token is `no_log`.
- Existing nodes aren't reinstalled or restarted (installs keep `creates:`).
- **Renovate** proposes `k3s_version` bumps (`k3s-upgrade` label, with a note to upgrade nodes first).
- `ansible-lint` on `k3s.yml`: 4 failures → 0.
- Also, in a separate commit: restores `specs/014-admin-ui-auth/plan.md` and `specs/015-pin-metallb-ips/plan.md`, which merged empty because of a truncation bug in my approval step.

## ⚠️ The pinned version is provisional
The cluster's live version isn't recorded anywhere (Terraform only creates the VMs), so this pins `v1.36.5+k3s1`. On your next `mise run k3s-install`:
- if it says nothing, the pin matches;
- if it stops with `<node> runs "k3s version vX.Y.Z+k3sN …" but k3s_version is …`, set `k3s_version` in `ansible/inventory.yml` to that value and push. Nothing on the nodes is changed by the failed run.

Merging changes nothing on the cluster by itself.

## Acceptance criteria
- [x] AC1: one `k3s_version` pins both installs
- [x] AC2: install script from the pinned tag
- [x] AC3: token never on a command line; `config.yaml` 0600; `no_log`
- [x] AC4: existing nodes not reinstalled
- [x] AC5: Renovate tracks `k3s_version`
- [x] AC6: version mismatch stops the playbook (tested locally with a fake `k3s`)

## How to verify
```
python3 specs/016-pin-k3s-version/check_k3s.py .
cd ansible && ansible-playbook --syntax-check -i inventory.yml playbooks/k3s.yml && ansible-lint playbooks/k3s.yml
```

## Follow-ups
- Existing workers still have `K3S_TOKEN` in `/etc/systemd/system/k3s-agent.service.env` from their original install. Removing it needs an agent restart.
- Upgrades: system-upgrade-controller (later phase).
- `proxmox.yml` needs the `ansible.posix` collection; no `requirements.yml` declares it.

Spec: `specs/016-pin-k3s-version/spec.md` · Plan: `specs/016-pin-k3s-version/plan.md`
Closes #16
