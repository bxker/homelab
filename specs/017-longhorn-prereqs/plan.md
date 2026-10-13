# Plan: Longhorn prerequisites on every k3s node, and keep multipathd off Longhorn's disks

Spec: [spec.md](spec.md) · Status: approved

## Callouts
- **New dependencies:** none (ansible.builtin only)
- **Public API / contract changes:** none
- **Migrations / data changes:** none
- **Security triggers touched:** none
- **Domains:** scripting (Ansible)
- **Environments affected on deploy:** none on merge; the next `mise run k3s-install` installs packages on
  the control plane and restarts multipathd once on nodes that have it
- **Destructive or replacing changes:** none

## Approach
New play "Install Longhorn prerequisites" on `k3s_cp:k3s_workers`, right after the version check and before
any k3s install: apt `open-iscsi` + `nfs-common`; `/etc/modules-load.d/iscsi_tcp.conf` and `modprobe
iscsi_tcp` only when `/sys/module/iscsi_tcp` is missing; `iscsid` enabled and started; `package_facts`, and
where `multipath-tools` is installed, `/etc/multipath/conf.d/longhorn.conf` (`blacklist { devnode
"^sd[a-z0-9]+" }`) notifying a `Restart multipathd` handler. The workers play drops its two prereq tasks.

## Files
| File | Change |
|---|---|
| `ansible/playbooks/k3s.yml` | new prereq play + handler; remove workers' prereq tasks |
| `docs/GETTING-STARTED.md` | how to confirm Longhorn sees every node |

## Test strategy
Run the new play on this sandbox (Ubuntu 24.04) with `connection: local`, real apt and files, `multipath-tools`
installed first so the drop-in path runs, and a `systemctl` stub for `iscsid`/`multipathd` (no systemd here).
Run 1: changes + one multipathd restart. Run 2: changed=0, no restart. Plus syntax-check, ansible-lint, and
#16's `check_k3s.py`.

## Tasks
- [ ] **T1** [agent: implementer] Prereq play for all k3s nodes
  - files: `ansible/playbooks/k3s.yml`
  - criteria: AC1, AC2, AC3, AC4
  - review: each
- [ ] **T2** [agent: implementer] Docs
  - files: `docs/GETTING-STARTED.md`
  - criteria: AC5
