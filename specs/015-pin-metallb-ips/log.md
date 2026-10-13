## analyst · spec · done
2026-10-13T03:19:50Z

**Did:** Wrote spec.md: 5 criteria (pins for Traefik, AdGuard DNS and UI, rewrite consistency, IP plan doc, optional static pool), 3 open questions.

**Evidence:**
- grep: only `adguard-home-http` pins an IP (`.203`, deprecated key); GETTING-STARTED:115 shows Traefik on `.201` vs rewrite `.200`

**Changed files:** `specs/015-pin-metallb-ips/spec.md`

**Open issues:** OQ1 live IPs (needs owner's kubectl output), OQ2 pool split, OQ3 single source

**Next:** Spec gate

## architect · plan · done
2026-10-13T03:22:04Z

**Did:** Wrote plan.md: 3 tasks (pool split, pins, docs); keep `homelab-pool` name to avoid prune/recreate.

**Evidence:**
- baseline renders (traefik 32.1.1, adguard, metallb 0.14.9) → lint 0 failed each; Traefik Service has only tailscale annotations
- metallb 0.14.9 CRD has `spec.autoAssign`

**Changed files:** `specs/015-pin-metallb-ips/plan.md`

**Open issues:** Router DHCP DNS → .201 is an owner step

**Next:** Plan gate

## implementer · T1 · done
2026-10-13T03:24:09Z

**Did:** Split MetalLB into `homelab-static` (.200–.209, autoAssign false) and `homelab-pool` (.210–.250, same name to avoid prune); L2Advertisement lists both.

**Evidence:**
- `check_ips.py` baseline → AC5 "one autoAssign:false pool" FAIL; after T1 → all 4 AC5 checks PASS; `helm lint` 0 failed

**Changed files:** `kubernetes/apps/infrastructure/metallb/templates/pool.yaml`

**Open issues:** none

**Next:** review T1

## infra-reviewer · T1 · done
2026-10-13T03:24:09Z

**Did:** Reviewed pool split (offline only, no cluster diff).

**Findings:**
- LOW: an unpinned LB Service now holding .200–.209 would move to .210+. Repo defines only Traefik, adguard-home-dns, adguard-home-http as LoadBalancer; all pinned in T2.
- LOW: apps sync independently, so a brief IP flap is possible before pins land (accepted, documented in plan).

**Open issues:** none

**Next:** commit T1, T2

## implementer · T2 · done
2026-10-13T03:24:32Z

**Did:** Pinned Traefik .200, AdGuard DNS .201, UI .203 with `metallb.io/loadBalancerIPs`; cross-reference comments on both sides of the rewrite IP.

**Evidence:**
- `check_ips.py` → RESULT: PASS (10/10); drifted rewrite (.201) → AC3 FAIL (check catches drift)
- `helm lint` traefik, adguard → 0 failed; rendered diff = 3 annotation lines only

**Changed files:** `traefik/values.yaml`, `adguard-home/templates/service.yaml`, `adguard-home/values.yaml`

**Open issues:** none

**Next:** review T2

## infra-reviewer · T2 · done
2026-10-13T03:24:32Z

**Did:** Reviewed T2 diff and renders (offline only).

**Findings:**
- MEDIUM (owner action): if live IPs differ, Services move on sync; LAN DNS breaks until the router's DHCP DNS is .201 → put it on the Deliver checklist, keep a secondary DNS.
- No new exposure; AdGuard ConfigMap unchanged (no pod restart).

**Open issues:** none

**Next:** commit T2, T3

## code-reviewer · batch (T3) · done
2026-10-13T03:25:11Z

**Did:** Read T3 docs diff against AC4.

**Findings:** none.

**Next:** Deliver gate
