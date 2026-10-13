# Verify: Require a login for the Longhorn, AdGuard and Traefik dashboard UIs

Run at 2026-10-13T03:39:42Z on commit `caf7b8d`.

## Checks
| Check | Command | Result |
|---|---|---|
| Tests | none in repo | not configured |
| Render | `specs/014-admin-ui-auth/render_all.sh` (helm v3.16.4; longhorn 1.8.2, traefik 32.1.1, adguard-home, ingress-auth) | pass |
| Lint | `helm lint` × 4 | pass: 0 failed each |
| Auth assertions | `python3 -I specs/014-admin-ui-auth/check_auth.py <render dir> .` | pass: 13/13 (baseline: 12 fail) |
| TOML / tasks | `tomllib` parse; `sh -n` on vault-write; #11 `verify_tasks.py` | pass (a `\$` escape bug was caught here and fixed before commit) |
| Plan / diff | — | offline only (no cluster access) |

## Acceptance criteria
| Criterion | Evidence | Result |
|---|---|---|
| AC1 | Longhorn Ingress annotated `longhorn-system-basic-auth@kubernetescrd`; dashboard IngressRoute `middlewares: [basic-auth]` | pass |
| AC2 | AdGuard Ingress `adguard.homelab.local` with `adguard-basic-auth@kubernetescrd`; no LoadBalancer targets port 3000 (`adguard-home-http` is ClusterIP) | pass |
| AC3 | ExternalSecret + Middleware `basic-auth` in longhorn-system, adguard, traefik from `secret/ingress-auth`.`htpasswd`; no `$2y$`/`$apr1$`/`{SHA}` strings under `kubernetes/` | pass |
| AC4 | `ingress-auth` wave 6 > external-secrets 5 and traefik 2; Traefik refuses routes with missing Middleware (fail closed) | pass (wave: render; refusal: Traefik behaviour, not run here) |
| AC5 | GETTING-STARTED: `bao kv put secret/ingress-auth`, protected-URL table, dashboard port-forward, how to protect another UI; `.203` removed from IP plan; CLAUDE.md + vault-write hint | pass |

## Notes
- Traefik v3.1.6 source confirms Middleware secrets with one key are parsed as htpasswd lines, and Traefik's ClusterRole reads secrets/middlewares cluster-wide.
- LoadBalancer→ClusterIP is accepted by the API server (`dropTypeDependentFields` clears nodePorts, k8s v1.31).
- Not checked live: 401 responses, ESO sync, Traefik's fail-closed behaviour.
- #15's `check_ips.py` AC2 (UI pinned at .203) now fails by design: superseded by this spec.
