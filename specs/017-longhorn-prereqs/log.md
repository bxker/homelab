## analyst · spec · done
2026-10-13T04:38:15Z

**Did:** Wrote spec.md: 5 criteria, 2 open questions (prereqs vs taint; blacklist vs disable multipathd).

**Evidence:**
- `k3s.yml`: prereqs + iscsid only in the workers play; Longhorn values set no nodeSelector/tolerations
- sandbox is Ubuntu 24.04 with apt access (open-iscsi 2.1.9-3ubuntu5.5, multipath-tools 0.9.4-5ubuntu8.2 available)

**Changed files:** `specs/017-longhorn-prereqs/spec.md`

**Next:** Spec gate
