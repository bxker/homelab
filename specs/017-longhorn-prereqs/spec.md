# Spec: Longhorn prerequisites on every k3s node, and keep multipathd off Longhorn's disks

Ticket: gh:17 · Size: standard · Status: approved

## Problem
Only workers get `open-iscsi`/`nfs-common` and a running `iscsid`, but the control plane is untainted, so
Longhorn's DaemonSets also run there and fail their environment check (likely a crash-looping
`longhorn-manager` on `k3s-cp-1`). Ubuntu's `multipathd` can also claim the iSCSI block devices Longhorn
attaches, which breaks volume mounts (Longhorn KB "troubleshooting volume with multipath").

## Goals
- Every node Longhorn may schedule on meets its prerequisites.
- multipathd never claims Longhorn's devices.

## Non-goals
- Tainting the control plane or moving Longhorn replicas (see OQ1; storage rework is #40).
- Encrypted volumes (`dm_crypt`).

## Acceptance criteria
- **AC1**: Given the playbook, then one play applies the Longhorn prerequisites to `k3s_cp` and `k3s_workers`:
  packages `open-iscsi` and `nfs-common`, `iscsid` enabled and running, and kernel module `iscsi_tcp` loaded
  now and at boot.
- **AC2**: Given a node with `multipath-tools` installed, then a drop-in
  `/etc/multipath/conf.d/longhorn.conf` blacklists `devnode "^sd[a-z0-9]+"`, and multipathd is restarted only
  when that file changes. Nodes without multipath-tools are left alone.
- **AC3**: Given a second run, then nothing changes and multipathd isn't restarted.
- **AC4**: Given the new play actually run on an Ubuntu 24.04 host (this sandbox, with a `systemctl` stub),
  then packages are installed, the module and config files exist, and the second run reports changed=0.
- **AC5**: Docs say how to confirm Longhorn sees every node as ready (`longhornctl check preflight` or the
  Longhorn UI's node status).

## Constraints
- Restarting multipathd doesn't remove maps that are in use; it stops multipathd from claiming new
  devices. That's the KB's documented fix.
- The VMs' root disk is `/dev/sda` (Proxmox scsi0). Blacklisting `sd*` only stops multipath from managing
  it, which it doesn't need (single path).

## Requirement changes
None.

## Open questions
None. Resolved at the Spec gate: (1) install the prerequisites on every node, no taint (revisit with #40);
(2) blacklist `sd*` with a multipath drop-in, keep the service.
