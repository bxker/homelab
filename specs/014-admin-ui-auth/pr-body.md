Require a login for the Longhorn, AdGuard and Traefik dashboard UIs

## Why
Longhorn's UI (can delete volumes) and AdGuard's UI (controls LAN DNS) accepted anyone on the LAN, and on the tailnet through the subnet router. One correction to #14: the Traefik dashboard was never LAN-exposed. Its route is on the internal `traefik` entrypoint (:9000), which the LoadBalancer doesn't publish. It gets the login anyway, as defense in depth.

## What changed
- **New app `ingress-auth`** (sync wave 6, after External Secrets): for `longhorn-system`, `adguard` and `traefik` it creates Secret `basic-auth` from OpenBao `secret/ingress-auth` (one bcrypt htpasswd line) and a Traefik `basicAuth` Middleware `basic-auth`.
- **Longhorn:** Ingress annotated `longhorn-system-basic-auth@kubernetescrd`.
- **Traefik dashboard:** IngressRoute `middlewares: [basic-auth]` (still internal-only).
- **AdGuard:** UI now at `https://adguard.homelab.local` through Traefik with the login; `adguard-home-http` is ClusterIP, which frees `.203`. DNS on `.201` is unchanged.
- Docs: credential step, protected-URL table, dashboard port-forward, how to protect another UI, IP plan, CLAUDE.md, `vault-write` hint.

## ⚠️ Before / after merging
Merging deploys via ArgoCD auto-sync (prune + self-heal).
1. **Before merging**, store the login. Until it exists, the three UIs return 404 (fail closed, never open):
   ```
   bao kv put secret/ingress-auth htpasswd="$(htpasswd -nbB admin 'YOUR_PASSWORD')"
   ```
2. After sync: `curl -sk -o /dev/null -w '%{http_code}\n' https://longhorn.homelab.local` → `401`, and the same for `https://adguard.homelab.local`. With `-u admin:YOUR_PASSWORD` both should return `200`.
3. The AdGuard UI no longer answers on `http://192.168.1.203`. Use `https://adguard.homelab.local`.

## Acceptance criteria
- [x] AC1: Longhorn Ingress and Traefik dashboard require the login
- [x] AC2: AdGuard UI only through the authenticated Ingress
- [x] AC3: credential only in OpenBao (bcrypt hash); nothing in Git
- [x] AC4: auth app syncs after ESO and Traefik; missing Middleware = route refused
- [x] AC5: docs updated

## How to verify
```
sh specs/014-admin-ui-auth/render_all.sh out/   # needs helm + chart deps; paths inside point at a scratch helm
python3 -I specs/014-admin-ui-auth/check_auth.py out/ .
```
13/13 pass (12 fail on `main`), and `helm lint` is clean for all four charts.

## Follow-ups
- The `metallb/templates/pool.yaml` comment still lists `.203 AdGuard UI` as a pin (cosmetic).
- SSO (#30) replaces this shared login.
- The ClusterSecretStore isn't namespace-scoped (#32).

Spec: `specs/014-admin-ui-auth/spec.md` · Plan: `specs/014-admin-ui-auth/plan.md`
Closes #14
