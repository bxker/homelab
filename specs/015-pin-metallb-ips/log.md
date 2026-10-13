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
