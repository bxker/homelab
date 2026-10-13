# Plan: Require a login for the Longhorn, AdGuard and Traefik dashboard UIs

Spec: [spec.md](spec.md) · Status: approved

## Callouts
- **New dependencies:** none (new wrapper chart `ingress-auth` with no subchart)
- **Public API / contract changes:** new OpenBao key `secret/ingress-auth` (`htpasswd`); AdGuard UI moves
  from `http://192.168.1.203` to `https://adguard.homelab.local`
- **Migrations / data changes:** none
- **Security triggers touched:** authentication, secrets, network exposure
- **Domains:** kubernetes, gitops
- **Environments affected on deploy:** homelab cluster via ArgoCD auto-sync (prune, selfHeal): new app
  `ingress-auth` (wave 6); `longhorn`, `traefik`, `adguard-home` change
- **Destructive or replacing changes:** `adguard-home-http` LoadBalancer → ClusterIP (releases `.203`).
  Until `secret/ingress-auth` exists, Longhorn/AdGuard/dashboard routes refuse requests (fail closed).

## Approach
New app `kubernetes/apps/infrastructure/ingress-auth/` (wave 6, after ESO 5 and Traefik's CRDs at 2). For
each namespace in `values.namespaces` (`longhorn-system`, `adguard`, `traefik`) it renders an
`ExternalSecret` → Secret `basic-auth` with one key `users` from `secret/ingress-auth` property `htpasswd`,
and a `traefik.io/v1alpha1` `Middleware` `basic-auth` (`basicAuth.secret: basic-auth`). One copy per
namespace avoids relying on cross-namespace references. Longhorn's chart Ingress gets
`traefik.ingress.kubernetes.io/router.middlewares: longhorn-system-basic-auth@kubernetescrd`; Traefik's
dashboard IngressRoute gets `middlewares: [{name: basic-auth}]`. AdGuard gains an Ingress
(`adguard.homelab.local`, `homelab-ca` TLS, `adguard-basic-auth@kubernetescrd`) to `adguard-home-http`,
which becomes ClusterIP. Traefik refuses a router whose Middleware doesn't exist yet, so a fresh bootstrap
fails closed until wave 6.

## Files
| File | Change |
|---|---|
| `kubernetes/apps/infrastructure/ingress-auth/{Chart.yaml,values.yaml,application.yaml}` | new app, wave 6 |
| `kubernetes/apps/infrastructure/ingress-auth/templates/basic-auth.yaml` | ExternalSecret + Middleware per namespace |
| `kubernetes/apps/infrastructure/longhorn/values.yaml` | middleware annotation on Ingress |
| `kubernetes/apps/infrastructure/traefik/values.yaml` | dashboard `middlewares` |
| `kubernetes/apps/infrastructure/adguard-home/templates/service.yaml` | UI Service → ClusterIP, drop .203 pin |
| `kubernetes/apps/infrastructure/adguard-home/templates/ingress.yaml` | new Ingress with auth |
| `docs/GETTING-STARTED.md`, `CLAUDE.md`, `mise.toml` | credential step, URLs, IP plan, waves, vault-write hint |

## Risks
- UIs unreachable until the owner writes `secret/ingress-auth`, mitigated by Deliver-gate steps (expected; fail closed).
- Anyone using `http://192.168.1.203` loses that URL, mitigated by docs + PR notes.

## Test strategy
Render all four charts with scratchpad helm; `check_auth.py` red on baseline, green after: middleware refs on
Longhorn Ingress, dashboard IngressRoute and AdGuard Ingress; ExternalSecret+Middleware per namespace;
no LoadBalancer exposes port 3000; no htpasswd/bcrypt strings in the repo; wave 6 > 5 and > 2. `helm lint` all.

## Tasks
- [ ] **T1** [agent: implementer] `ingress-auth` app
  - files: `kubernetes/apps/infrastructure/ingress-auth/Chart.yaml`, `kubernetes/apps/infrastructure/ingress-auth/values.yaml`, `kubernetes/apps/infrastructure/ingress-auth/application.yaml`, `kubernetes/apps/infrastructure/ingress-auth/templates/basic-auth.yaml`
  - criteria: AC3, AC4
  - review: each
- [ ] **T2** [agent: implementer] Attach auth to Longhorn Ingress and Traefik dashboard
  - files: `kubernetes/apps/infrastructure/longhorn/values.yaml`, `kubernetes/apps/infrastructure/traefik/values.yaml`
  - criteria: AC1
  - review: each
- [ ] **T3** [agent: implementer] AdGuard UI behind Traefik; Service → ClusterIP
  - files: `kubernetes/apps/infrastructure/adguard-home/templates/service.yaml`, `kubernetes/apps/infrastructure/adguard-home/templates/ingress.yaml`
  - criteria: AC2
  - review: each
- [ ] **T4** [agent: implementer] Docs, IP plan, vault-write hint
  - files: `docs/GETTING-STARTED.md`, `CLAUDE.md`, `mise.toml`
  - criteria: AC5
