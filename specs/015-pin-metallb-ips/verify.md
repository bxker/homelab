# Verify: Pin MetalLB IPs for Traefik and AdGuard

Run at 2026-10-13T03:24:48Z on commit `8be5882`.

## Checks
| Check | Command | Result |
|---|---|---|
| Tests | none in repo | not configured |
| Render | helm v3.16.4: traefik (chart 32.1.1 packaged from tag `v32.1.1`), adguard-home (local), metallb (0.14.9 release) | pass |
| Lint | `helm lint` × 3 | pass: 0 failed each |
| IP assertions | `python3 -I specs/015-pin-metallb-ips/check_ips.py <traefik> <adguard> <metallb> .` | pass: 10/10 (baseline: 7 fail) |
| Negative | same check with the rewrite drifted to .201 | AC3 fails as expected |
| Plan / diff | — | offline only (no cluster access) |

## Acceptance criteria
| Criterion | Evidence | Result |
|---|---|---|
| AC1 | Rendered Traefik LoadBalancer Service: `metallb.io/loadBalancerIPs: 192.168.1.200` | pass |
| AC2 | `adguard-home-dns` → .201, `adguard-home-http` → .203; `grep -rn metallb.universe.tf kubernetes/` → none | pass |
| AC3 | Rewrite answer `192.168.1.200` == Traefik pin; drift test fails AC3 | pass |
| AC4 | GETTING-STARTED: IP plan rows for .200/.201/.203 and both pools; hosts example .200; router DHCP DNS .201 | pass |
| AC5 | Pools `homelab-static` 200–209 `autoAssign: false`, `homelab-pool` 210–250; no overlap; all pins in static; L2Advertisement lists both | pass |

## Notes
- ArgoCD resolves `32.*`/`0.14.*` from Helm repo indexes this environment can't reach; 32.1.1 (newest v32 tag) and 0.14.9 (newest 0.14.x in the MetalLB index) were used.
- Not checked live: which IPs Services hold now, IP moves on sync, router DHCP.
