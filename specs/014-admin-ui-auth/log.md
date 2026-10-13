## analyst · spec · done
2026-10-13T03:35:18Z

**Did:** Wrote spec.md: 5 criteria, 4 open questions. Corrected the ticket: Traefik dashboard isn't LAN-exposed.

**Evidence:**
- rendered traefik 32.1.1: dashboard IngressRoute `entryPoints: [traefik]`; LB Service ports 80/443 only
- traefik v3.1.6 `crd/kubernetes.go`: `kubernetes.io/basic-auth` Secrets supported, hashed as `{SHA}` (unsalted SHA-1)

**Changed files:** `specs/014-admin-ui-auth/spec.md`

**Open issues:** OQ1 AdGuard approach, OQ2 credential format, OQ3 dashboard, OQ4 shared login

**Next:** Spec gate

## architect · plan · done
2026-10-13T03:37:15Z

**Did:** Wrote plan.md: 4 tasks. New wave-6 app `ingress-auth` holds ExternalSecret + Middleware per namespace (avoids the ESO-before-Traefik/Longhorn ordering problem and cross-namespace refs).

**Evidence:**
- traefik 32.1.1 `templates/ingressroute.yaml` passes `dashboard.middlewares` through to the route
- traefik v3.1.6: non-basic-auth-type Secret must have exactly one key (htpasswd lines)

**Changed files:** `specs/014-admin-ui-auth/plan.md`

**Open issues:** none

**Next:** Plan gate
