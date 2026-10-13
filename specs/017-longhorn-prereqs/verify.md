# Verify: Longhorn prerequisites on every k3s node, and keep multipathd off Longhorn's disks

Run at 2026-10-13T05:04:43Z on commit `8f717f4`.

## Checks
| Check | Command | Result |
|---|---|---|
| Syntax | `uvx --from ansible-core ansible-playbook --syntax-check -i ansible/inventory.yml ansible/playbooks/k3s.yml` | pass |
| Lint | `uvx ansible-lint ansible/playbooks/k3s.yml` | pass, production profile |
| Regression | #16 `check_k3s.py` | pass |
| Real run | the new play on this Ubuntu 24.04 sandbox (`connection: local`, `/usr/bin/python3.12`, stubs for `systemctl` and `modprobe`) | run 1 ok=10 changed=6; run 2 see AC3 |
| multipath | `multipath -t` after run 1 | `devnode "^sd[a-z0-9]+"` in the effective blacklist |
| Merge | `git merge-tree` with #49's branch | no conflict |

## Acceptance criteria
| Criterion | Evidence | Result |
|---|---|---|
| AC1 | Play on `k3s_cp:k3s_workers`; run 1 installed `open-iscsi 2.1.9-3ubuntu5.5`, `nfs-common 1:2.6.4-3ubuntu5.1`, wrote `/etc/modules-load.d/iscsi_tcp.conf`, called `modprobe iscsi_tcp` and `systemctl … iscsid` | pass |
| AC2 | Drop-in `/etc/multipath/conf.d/longhorn.conf` (root 0644) only where `multipath-tools` is installed; handler restarted multipathd once | pass |
| AC3 | Run 2: no multipathd restart, all tasks ok except "Load iscsi_tcp now", which re-ran only because the `modprobe` stub can't create `/sys/module/iscsi_tcp` (a real `modprobe` does, so the task is skipped on real nodes) | pass (with that stub caveat) |
| AC4 | Runs above on Ubuntu 24.04 | pass |
| AC5 | GETTING-STARTED "Check that Longhorn can use every node" | pass |

## Notes
- No systemd and no kernel modules in the sandbox; service and module calls were stubbed and recorded. Packages and files were real. The test files were removed afterwards.
