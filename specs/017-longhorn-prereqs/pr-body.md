Install Longhorn prerequisites on every k3s node; keep multipathd off its disks

## Why
Only the workers got `open-iscsi`/`nfs-common` and a running `iscsid`. The control plane isn't tainted, so Longhorn's DaemonSets run there too and fail their environment check (`longhorn-manager` likely crash-looping on `k3s-cp-1`). Separately, Ubuntu's `multipathd` can claim the iSCSI disks Longhorn attaches and break volume mounts ([Longhorn KB](https://longhorn.io/kb/troubleshooting-volume-with-multipath/)).

## What changed
- New play **"Install Longhorn prerequisites"** on `k3s_cp` **and** `k3s_workers`, before any k3s install:
  - `open-iscsi`, `nfs-common`;
  - `iscsi_tcp` loaded now and at boot;
  - `iscsid` enabled and running.
- Where `multipath-tools` is installed: `/etc/multipath/conf.d/longhorn.conf` blacklists `devnode "^sd[a-z0-9]+"`, and `multipathd` restarts only when that file changes.
- The workers-only copy of these tasks is removed.
- `docs/GETTING-STARTED.md`: how to confirm Longhorn can use every node.

No taint on the control plane. That would mean draining any Longhorn replicas off its disk first, which fits with the storage rework (#40).

## What your next `mise run k3s-install` does
It installs the packages on the control plane, loads `iscsi_tcp`, and restarts `multipathd` once per node. No k3s restart. Afterwards, `kubectl -n longhorn-system get nodes.longhorn.io` should show every node Ready and Schedulable. Merging changes nothing by itself.

## Acceptance criteria
- [x] AC1: prerequisites on every k3s node
- [x] AC2: multipath drop-in + restart only on change
- [x] AC3: re-run changes nothing on real nodes (see the stub caveat below)
- [x] AC4: run for real on Ubuntu 24.04
- [x] AC5: docs

## How it was tested
I ran the play twice on an Ubuntu 24.04 sandbox: real apt and files, with `systemctl`/`modprobe` stubbed because the sandbox has no systemd or kernel modules.
- **Run 1** installed the packages, wrote both files and restarted `multipathd` once.
- **Run 2** didn't restart anything. It re-ran only "Load iscsi_tcp now", because the stub can't create `/sys/module/iscsi_tcp`; on a real node that task is skipped.
- `multipath -t` confirms the blacklist is merged.
- `ansible-lint` passes the production profile, and the PR merges cleanly with #49.

## Follow-ups
- Tainting the control plane, if wanted, goes with #40.

Spec: `specs/017-longhorn-prereqs/spec.md` · Plan: `specs/017-longhorn-prereqs/plan.md`
Closes #17
