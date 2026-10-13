## analyst · spec · done
2026-10-13T03:19:50Z

**Did:** Wrote spec.md: 5 criteria (pins for Traefik, AdGuard DNS and UI, rewrite consistency, IP plan doc, optional static pool), 3 open questions.

**Evidence:**
- grep: only `adguard-home-http` pins an IP (`.203`, deprecated key); GETTING-STARTED:115 shows Traefik on `.201` vs rewrite `.200`

**Changed files:** `specs/015-pin-metallb-ips/spec.md`

**Open issues:** OQ1 live IPs (needs owner's kubectl output), OQ2 pool split, OQ3 single source

**Next:** Spec gate
