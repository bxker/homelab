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

## implementer · T1 · done
2026-10-13T03:38:23Z

**Did:** New app `ingress-auth` (wave 6): per namespace (longhorn-system, adguard, traefik) an ExternalSecret `basic-auth` (key `users` ← `secret/ingress-auth`.`htpasswd`) and a `traefik.io/v1alpha1` basicAuth Middleware (`removeHeader: true`).

**Evidence:**
- `check_auth.py` red on baseline (AC3/AC4 FAIL); after T1 → all AC3/AC4 PASS; `helm lint` 0 failed; 6 resources rendered

**Changed files:** `kubernetes/apps/infrastructure/ingress-auth/{Chart.yaml,values.yaml,application.yaml,templates/basic-auth.yaml}`

**Open issues:** none

**Next:** review T1

## infra-reviewer + security-reviewer · T1 · done
2026-10-13T03:38:23Z

**Did:** Reviewed the new app and Traefik's rendered RBAC/provider args (offline).

**Findings:**
- none CRITICAL/HIGH. Traefik ClusterRole has get/list/watch on secrets and middlewares; providers unscoped.
- LOW: app has no CreateNamespace. It relies on the three namespaces existing (waves 2–3); on a fresh bootstrap they do by wave 6.
- LOW (pre-existing, #32): ClusterSecretStore isn't namespace-scoped.

**Next:** commit T1, T2

## implementer · T2 · done
2026-10-13T03:38:38Z

**Did:** Longhorn Ingress annotated with `longhorn-system-basic-auth@kubernetescrd`; Traefik dashboard IngressRoute gets `middlewares: [{name: basic-auth}]`.

**Evidence:**
- `check_auth.py` AC1 ×2 PASS; `helm lint` 0 failed ×2; rendered diff = 3 added lines

**Changed files:** `longhorn/values.yaml`, `traefik/values.yaml`

**Open issues:** none

**Next:** review T2

## infra-reviewer + security-reviewer · T2 · done
2026-10-13T03:38:38Z

**Findings:** none. Until `ingress-auth` syncs, both routes are refused (fail closed); Longhorn UI becomes unreachable until `secret/ingress-auth` is written (expected, on the Deliver checklist).

**Next:** commit T2, T3

## implementer · T3 · done
2026-10-13T03:39:12Z

**Did:** AdGuard UI Ingress at `adguard.homelab.local` (homelab-ca TLS, `adguard-basic-auth@kubernetescrd`); `adguard-home-http` → ClusterIP (drops the .203 pin).

**Evidence:**
- `check_auth.py` → RESULT: PASS (13/13); `helm lint` 0 failed
- k8s v1.31 `service/strategy.go` `dropTypeDependentFields` zeroes nodePorts on LoadBalancer→ClusterIP

**Changed files:** `adguard-home/templates/service.yaml`, `adguard-home/templates/ingress.yaml`

**Open issues:** `metallb/templates/pool.yaml` comment still lists ".203 AdGuard UI" (outside task scope → Deliver gate)

**Next:** review T3

## infra-reviewer + security-reviewer · T3 · done
2026-10-13T03:39:12Z

**Findings:**
- LOW: stale pin comment in metallb pool.yaml (see above).
- LOW: #15's `check_ips.py` AC2 (UI pinned .203) now fails by design; superseded by this spec.
- No new exposure: UI moves from an unauthenticated LB IP to an authenticated Ingress.

**Next:** commit T3, T4
