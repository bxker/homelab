# Spec: Pin MetalLB IPs for Traefik and AdGuard

Ticket: gh:15 · Size: standard · Status: approved

## Problem
Traefik's and AdGuard DNS's LoadBalancer IPs are whatever MetalLB hands out first, but
AdGuard rewrites `*.homelab.local` to a hardcoded `192.168.1.200` and the router's DHCP points
clients at the DNS IP. A different creation order (fresh bootstrap, rebuild, Service recreate)
silently breaks all `*.homelab.local` names or LAN DNS. The docs already disagree: GETTING-STARTED
shows Traefik on `.201` while the rewrite targets `.200`.

## Goals
- Traefik, AdGuard DNS, and AdGuard UI always get the same, documented IPs.
- The AdGuard rewrite target can't drift from Traefik's IP unnoticed.

## Non-goals
- Changing which services are exposed, or Tailscale exposure (#35). DNS HA (#22).

## Acceptance criteria
- **AC1**: Given the rendered `traefik` chart, then its LoadBalancer Service carries
  `metallb.io/loadBalancerIPs: 192.168.1.200`.
- **AC2**: Given the rendered `adguard-home` chart, then `adguard-home-dns` carries
  `metallb.io/loadBalancerIPs: 192.168.1.201` and `adguard-home-http` carries `192.168.1.203`; no
  `metallb.universe.tf/` annotation remains in the repo.
- **AC3**: Given the rendered `adguard-home` ConfigMap, then the `*.homelab.local` rewrite answer equals
  `192.168.1.200`, and an offline check fails if the Traefik and AdGuard values disagree.
- **AC4**: Given `docs/GETTING-STARTED.md`, then an IP plan lists every pinned LB IP, the `/etc/hosts`
  example uses `192.168.1.200`, and it says the router's DHCP DNS should be `192.168.1.201`.
- **AC5**: pinned IPs come from a pool with `autoAssign: false`; other LB Services get
  IPs only from a separate dynamic pool, and every pinned IP falls inside the static pool.

## Constraints
- Pinning a Service to an IP other than its current one makes MetalLB move it on sync. Pins
  must match live assignments unless the owner accepts the move (OQ1).
- Traefik and AdGuard are separate Helm releases; a value can't be shared between them directly.

## Requirement changes
None.

## Open questions
None. Resolved at the Spec gate:
1. Pin Traefik `.200`, AdGuard DNS `.201`, AdGuard UI `.203` (ticket's values); the owner accepts that Services
   may move and will point the router's DHCP DNS at `.201`.
2. Split the pool: `static` 200–209 (`autoAssign: false`) + dynamic 210–250.
3. Default: IP kept in both values files with cross-reference comments + offline consistency check.
