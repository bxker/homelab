# Plan: Pin MetalLB IPs for Traefik and AdGuard

Spec: [spec.md](spec.md) · Status: draft

## Callouts
- **New dependencies:** none
- **Public API / contract changes:** LAN-facing IPs become fixed: Traefik `.200`, AdGuard DNS `.201`, UI `.203`
- **Migrations / data changes:** none
- **Security triggers touched:** network exposure (IPs only; nothing newly exposed)
- **Domains:** kubernetes, gitops
- **Environments affected on deploy:** homelab cluster via ArgoCD auto-sync (`prune`, `selfHeal`) of apps
  `metallb` (wave 1), `traefik`, `adguard-home` (wave 2)
- **Destructive or replacing changes:** none deleted. Services whose current IP differs from their pin
  **move** (accepted at Spec gate). Apps sync independently, so for a short window MetalLB may give an
  unpinned Service a `.210+` IP before its pin lands.

## Approach
Keep pool `homelab-pool` (renaming would prune and recreate it) and narrow it to the dynamic range
`192.168.1.210-250`; add `homelab-static` `192.168.1.200-209` with `autoAssign: false`; the existing
`L2Advertisement` lists both. Pin Traefik through the chart's `service.annotations`, and AdGuard's two
Services with `metallb.io/loadBalancerIPs` (replacing the deprecated `metallb.universe.tf/` key). AdGuard's
`traefikIP` stays the rewrite source, with comments in both values files pointing at each other, and
`specs/015-pin-metallb-ips/check_ips.py` (renders all three charts' output) asserts: Traefik pin ==
rewrite answer, every pin is inside the static pool, pools don't overlap, no deprecated key in the repo.

## Files
| File | Change |
|---|---|
| `kubernetes/apps/infrastructure/metallb/templates/pool.yaml` | dynamic 210–250 + new static pool, L2 adv lists both |
| `kubernetes/apps/infrastructure/traefik/values.yaml` | `metallb.io/loadBalancerIPs: 192.168.1.200` + cross-ref |
| `kubernetes/apps/infrastructure/adguard-home/templates/service.yaml` | DNS `.201`, UI `.203` on new key |
| `kubernetes/apps/infrastructure/adguard-home/values.yaml` | cross-ref comment on `traefikIP` |
| `docs/GETTING-STARTED.md` | IP plan rows, `/etc/hosts` example `.200`, router DHCP DNS `.201` |

## Risks
- LAN DNS outage if the router still points at an old DNS IP, mitigated by a Deliver-gate step: set router DHCP DNS to `.201` (and keep a secondary).
- Transient IP flap during sync, mitigated by documenting the post-merge check (`kubectl get svc -A --field-selector spec.type=LoadBalancer`).

## Test strategy
Render before/after with scratchpad helm v3.16.4 (traefik 32.1.1 packaged from tag, metallb 0.14.9 release,
adguard local); `check_ips.py` red on baseline, green after; `helm lint` all three; grep docs.

## Tasks
- [ ] **T1** [agent: implementer] Split MetalLB pool
  - files: `kubernetes/apps/infrastructure/metallb/templates/pool.yaml`
  - criteria: AC5
  - review: each
- [ ] **T2** [agent: implementer] Pin Traefik and AdGuard Services; cross-reference the rewrite IP
  - files: `kubernetes/apps/infrastructure/traefik/values.yaml`, `kubernetes/apps/infrastructure/adguard-home/templates/service.yaml`, `kubernetes/apps/infrastructure/adguard-home/values.yaml`
  - criteria: AC1, AC2, AC3
  - review: each
- [ ] **T3** [agent: implementer] IP plan and hosts example in docs
  - files: `docs/GETTING-STARTED.md`
  - criteria: AC4
