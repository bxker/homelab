## analyst · spec · done
2026-10-13T04:38:15Z

**Did:** Wrote spec.md: 5 criteria, 2 open questions (prereqs vs taint; blacklist vs disable multipathd).

**Evidence:**
- `k3s.yml`: prereqs + iscsid only in the workers play; Longhorn values set no nodeSelector/tolerations
- sandbox is Ubuntu 24.04 with apt access (open-iscsi 2.1.9-3ubuntu5.5, multipath-tools 0.9.4-5ubuntu8.2 available)

**Changed files:** `specs/017-longhorn-prereqs/spec.md`

**Next:** Spec gate

## architect · plan · done
2026-10-13T05:01:22Z

**Did:** Wrote plan.md: one shared play + handler, tested for real on the Ubuntu 24.04 sandbox.

**Changed files:** `specs/017-longhorn-prereqs/plan.md`

**Next:** Plan gate

## implementer · T1 · done
2026-10-13T05:04:20Z

**Did:** New "Install Longhorn prerequisites" play on `k3s_cp:k3s_workers` (apt open-iscsi/nfs-common, iscsi_tcp at boot + now, iscsid, multipath drop-in + restart handler); removed the workers-only copy.

**Evidence:**
- syntax-check ok; ansible-lint production; #16 `check_k3s.py` PASS (version check still first play)
- sandbox (Ubuntu 24.04, system python3.12, stubs for systemctl/modprobe): run1 ok=10 changed=6, one `systemctl restart multipathd`; run2 changed=1 (only "Load iscsi_tcp now": the modprobe stub can't create /sys/module/iscsi_tcp), no multipathd restart
- `multipath -t` shows `devnode "^sd[a-z0-9]+"` merged into the blacklist

**Changed files:** `ansible/playbooks/k3s.yml`

## infra-reviewer · T1 · done
2026-10-13T05:04:20Z

**Findings:** none CRITICAL/HIGH. LOW: restarting multipathd doesn't release maps already in use; if a Longhorn volume was already claimed, a node reboot clears it (noted in docs).

**Next:** commit T1, T2

## implementer · T2 · done
2026-10-13T05:05:07Z

**Did:** GETTING-STARTED "Check that Longhorn can use every node" (placed away from #49's edits; merge-tree clean).

**Changed files:** `docs/GETTING-STARTED.md`

## code-reviewer · batch (T2) · done
2026-10-13T05:05:07Z

**Findings:** none.

**Next:** Deliver gate
