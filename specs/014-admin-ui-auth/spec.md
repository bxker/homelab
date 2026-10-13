# Spec: Require a login for the Longhorn and AdGuard admin UIs

Ticket: gh:14 · Size: standard · Status: draft

## Problem
Longhorn's UI (`longhorn.homelab.local`, can delete volumes) and AdGuard's UI (`192.168.1.203`, controls
LAN DNS) accept anyone on the LAN, and on the tailnet via the subnet router. Correction to the ticket: the
Traefik dashboard is **not** LAN-exposed: its IngressRoute uses the `traefik` entrypoint (:9000), which
the LoadBalancer Service doesn't publish (only 80/443, checked in the rendered chart).

## Goals
- Longhorn and AdGuard UIs require credentials; nothing about the credentials is in Git.
- A fresh bootstrap never serves those UIs without auth, even briefly.

## Non-goals
- SSO/OIDC (#30). Auth on UIs that have their own login (ArgoCD, Grafana, OpenBao, Seafile).
- AdGuard replicas/persistence (#22).

## Acceptance criteria
- **AC1**: Given the rendered Longhorn chart, then its Ingress references a `basicAuth` Middleware in
  `longhorn-system` via `traefik.ingress.kubernetes.io/router.middlewares`.
- **AC2**: Given the rendered AdGuard config, then the UI is reachable from outside the cluster only
  through an auth-protected route (see OQ1); no LoadBalancer serves the UI port without auth.
- **AC3**: Given the repo, then credentials come only from OpenBao via an `ExternalSecret`; `grep` finds no
  htpasswd hash or password in Git.
- **AC4**: Given a fresh bootstrap, then the Middlewares and their Secrets sync after External Secrets
  (wave 5) and Traefik's CRDs, and a route whose Middleware is missing is refused (fail closed), not served.
- **AC5**: Given the docs, then `docs/GETTING-STARTED.md` explains creating the credential, lists the
  protected URLs, notes the dashboard is reached by port-forward, and the IP plan matches OQ1's outcome.

## Constraints
- Traefik v3.1.6 (chart 32.1.1). Middlewares in the `kubernetescrd` provider; Ingress references them as
  `<namespace>-<name>@kubernetescrd`.
- Traefik and Longhorn sync before ESO (waves 2/3 < 5), so their own charts can't hold an ExternalSecret.
- Live 401 checks are the owner's (no cluster access here).

## Requirement changes
None.

## Open questions
1. **AdGuard:** *its UI is on its own LoadBalancer (.203), not behind Traefik.* Recommended: serve it at
   `adguard.homelab.local` through Traefik with the same basic-auth, and turn `adguard-home-http` into a
   ClusterIP (frees .203). Alternative: AdGuard's own `users:` login, which needs the DNS pod to read a
   Secret at start-up. A missing Secret would then stop LAN DNS.
2. **Credential format:** Recommended: an `htpasswd -nbB` bcrypt line in OpenBao `secret/ingress-auth`
   (the cluster only ever holds the hash). Alternative: plain username/password (`kubernetes.io/basic-auth`),
   which is simpler, but Traefik hashes it with unsalted SHA-1 and the plaintext sits in the Secret.
3. **Traefik dashboard:** Recommended: leave it internal-only and document `kubectl port-forward`.
   Alternatives: add the same auth anyway, or disable it.
4. **One login or one per UI?** Recommended: one shared login until SSO (#30).
