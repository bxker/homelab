## analyst · spec · done
2026-10-13T03:35:18Z

**Did:** Wrote spec.md: 5 criteria, 4 open questions. Corrected the ticket: Traefik dashboard isn't LAN-exposed.

**Evidence:**
- rendered traefik 32.1.1: dashboard IngressRoute `entryPoints: [traefik]`; LB Service ports 80/443 only
- traefik v3.1.6 `crd/kubernetes.go`: `kubernetes.io/basic-auth` Secrets supported, hashed as `{SHA}` (unsalted SHA-1)

**Changed files:** `specs/014-admin-ui-auth/spec.md`

**Open issues:** OQ1 AdGuard approach, OQ2 credential format, OQ3 dashboard, OQ4 shared login

**Next:** Spec gate
