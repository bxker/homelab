# Spec: Pin MetalLB IPs for Traefik and AdGuard

Ticket: gh:15 · Size: standard · Status: draft

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
  `metallb.io/loadBalancerIPs: <TRAEFIK_IP>`.
- **AC2**: Given the rendered `adguard-home` chart, then `adguard-home-dns` carries
  `metallb.io/loadBalancerIPs: <DNS_IP>` and `adguard-home-http` carries `<UI_IP>`; no
  `metallb.universe.tf/` annotation remains in the repo.
- **AC3**: Given the rendered `adguard-home` ConfigMap, then the `*.homelab.local` rewrite answer equals
  `<TRAEFIK_IP>`, and an offline check fails if the Traefik and AdGuard values disagree.
- **AC4**: Given `docs/GETTING-STARTED.md`, then an IP plan lists every pinned LB IP, the `/etc/hosts`
  example uses `<TRAEFIK_IP>`, and it says the router's DHCP DNS should be `<DNS_IP>`.
- **AC5** (if OQ2 = yes): pinned IPs come from a pool with `autoAssign: false`; other LB Services get
  IPs only from a separate dynamic pool, and every pinned IP falls inside the static pool.

## Constraints
- Pinning a Service to an IP other than its current one makes MetalLB move it on sync. Pins
  must match live assignments unless the owner accepts the move (OQ1).
- Traefik and AdGuard are separate Helm releases; a value can't be shared between them directly.

## Requirement changes
None.

## Open questions
1. **Which IPs?** *Pinning anything other than the live IPs moves Services; if AdGuard DNS moves,
   every LAN client loses DNS until the router's DHCP is updated.* Please run
   `kubectl get svc -A --field-selector spec.type=LoadBalancer` and say which IPs Traefik and
   `adguard-home-dns` have now, and what DNS IP the router hands out. Recommended: pin to the live IPs.
   Alternative: the ticket's `.200`/`.201`, accepting a move and a router change.
2. **Split the pool?** Recommended: yes, `static` 200–209 (`autoAssign: false`) + `dynamic` 210–250,
   *so a future LB Service can't take a pinned IP before its owner exists on a fresh bootstrap*.
   Safe only if no other LB Service currently holds an IP in 200–209 (the same `kubectl` output shows this).
3. **Single source for the Traefik IP:** separate releases can't share values. Recommended: keep the IP
   in both values files, each with a comment pointing at the other, plus an offline check (AC3) run in
   verify and later in CI (#28).
