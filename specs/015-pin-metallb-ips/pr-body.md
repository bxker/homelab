Pin MetalLB IPs for Traefik and AdGuard; split static/dynamic pools

## Why
Traefik and AdGuard DNS took whatever IP MetalLB handed out first, while AdGuard rewrites `*.homelab.local` to a hardcoded `.200` and the router hands out the DNS IP. A different creation order (rebuild, fresh bootstrap, Service recreate) silently broke name resolution or LAN DNS. The docs already disagreed: they showed Traefik on `.201`.

## What changed
- **MetalLB:** new `homelab-static` pool (`.200–.209`, `autoAssign: false`) for pinned Services; `homelab-pool` narrowed to `.210–.250` (same name, updated in place).
- **Pins** via `metallb.io/loadBalancerIPs`: Traefik `.200`, AdGuard DNS `.201`, AdGuard UI `.203` (moved off the deprecated `metallb.universe.tf/` key).
- Comments on both sides tie AdGuard's `traefikIP` to Traefik's pin.
- `docs/GETTING-STARTED.md`: IP plan for both pools and every pin, hosts example fixed to `.200`, router DHCP DNS `.201`.

## ⚠️ Before / after merging
Merging deploys: ArgoCD auto-syncs `metallb`, `traefik` and `adguard-home` from `main` (prune + self-heal).
1. Check current IPs: `kubectl get svc -A --field-selector spec.type=LoadBalancer`. Any of Traefik / `adguard-home-dns` / `adguard-home-http` not already on `.200` / `.201` / `.203` will **move**.
2. Apps sync independently, so for a minute a Service may briefly get a `.210+` IP before its pin lands.
3. Point the router's DHCP DNS at **`192.168.1.201`**, and keep a secondary (router or upstream) so clients aren't stranded.
4. Re-run step 1 and confirm `.200` / `.201` / `.203`; `dig @192.168.1.201 grafana.homelab.local` → `192.168.1.200`.

## Acceptance criteria
- [x] AC1: Traefik pinned to `.200`
- [x] AC2: AdGuard DNS `.201`, UI `.203`; no deprecated key left
- [x] AC3: rewrite target == Traefik pin, with a check that fails on drift
- [x] AC4: IP plan documented
- [x] AC5: static pool (no auto-assign) holds every pin; pools don't overlap

## How to verify
```
# render traefik, adguard-home, metallb (helm + chart deps), then:
python3 -I specs/015-pin-metallb-ips/check_ips.py traefik.yaml adguard.yaml metallb.yaml .
```
10/10 pass (7 fail on `main`), and `helm lint` is clean for all three charts. Rendered with helm v3.16.4, traefik 32.1.1 and metallb 0.14.9.

## Follow-ups
- Run `check_ips.py` in CI (#28).
- AdGuard is still a single replica (#22); keep a secondary DNS in DHCP until then.

Spec: `specs/015-pin-metallb-ips/spec.md` · Plan: `specs/015-pin-metallb-ips/plan.md`
Closes #15
