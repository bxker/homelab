# Plan: Source the Grafana admin password from OpenBao

Spec: [spec.md](spec.md) · Status: approved

## Callouts
- **New dependencies:** none
- **Public API / contract changes:** new required OpenBao key `secret/grafana` (`admin_user`, `admin_password`)
- **Migrations / data changes:** none (Grafana PVC untouched; DB password reset is a manual runbook step)
- **Security triggers touched:** secrets / config loading
- **Domains:** kubernetes, gitops
- **Environments affected on deploy:** the homelab cluster: ArgoCD auto-syncs `main` (`prune: true`,
  `selfHeal: true`) for app `prometheus-stack` in `monitoring`
- **Destructive or replacing changes:** ArgoCD prunes chart Secret `monitoring/prometheus-stack-grafana`
  (no longer rendered) and restarts the Grafana pod. If `secret/grafana` isn't in OpenBao before merge,
  Grafana stays in `CreateContainerConfigError` until it is.

## Approach
Reuse the Seafile/Tailscale pattern: a wrapper-chart template `templates/grafana-admin-secret.yaml`,
an `external-secrets.io/v1` `ExternalSecret` against ClusterSecretStore `openbao`, `creationPolicy: Owner`,
`refreshInterval: 1h`, target `grafana-admin` with `admin-user`/`admin-password` from `secret/grafana`.
Values drop `grafana.adminPassword` and set `grafana.admin.existingSecret: grafana-admin` (keys are the
chart defaults, written explicitly). Grafana 8.5.12 then skips its own Secret and points the container
and the dashboard/datasource sidecars at `grafana-admin` (checked in `_pod.tpl`, `secret.yaml`).
`application.yaml` moves to sync wave 6 so the ESO CRD (wave 5) exists on fresh bootstraps.
Docs get the new key and a rotation runbook (the DB keeps the old password until reset).

## Files
| File | Change |
|---|---|
| `kubernetes/apps/infrastructure/prometheus-stack/templates/grafana-admin-secret.yaml` | new: ExternalSecret |
| `kubernetes/apps/infrastructure/prometheus-stack/values.yaml` | remove `adminPassword`; add `admin.existingSecret` |
| `kubernetes/apps/infrastructure/prometheus-stack/application.yaml` | sync-wave `4` → `6` |
| `docs/GETTING-STARTED.md` | Step 6 `bao kv put secret/grafana`; rotation runbook |
| `mise.toml` | `vault-write` hint lists `secret/grafana` |
| `CLAUDE.md` | Secrets section (no placeholders; OpenBao+ESO); sync-wave list |

## Risks
- Grafana down after merge if the OpenBao key is missing, mitigated by Deliver-gate checklist + runbook order.
- Sidecar reload auth fails if DB password ≠ Secret, mitigated by the runbook's reset step.

## Test strategy
Render with pinned helm (vendored chart 65.8.1, same as `65.*` resolves to) before/after: AC1–AC2 from
rendered YAML (ExternalSecret present; no `admin-password` literal; env refs `grafana-admin`); `helm lint`;
AC3 grep; AC4 wave value vs ESO's; AC5 doc grep. No cluster access.

## Tasks
- [ ] **T1** [agent: implementer] ExternalSecret + values + sync wave
  - files: `kubernetes/apps/infrastructure/prometheus-stack/templates/grafana-admin-secret.yaml`, `kubernetes/apps/infrastructure/prometheus-stack/values.yaml`, `kubernetes/apps/infrastructure/prometheus-stack/application.yaml`
  - criteria: AC1, AC2, AC3, AC4
  - review: each
- [ ] **T2** [agent: implementer] Docs, vault-write hint, rotation runbook
  - files: `docs/GETTING-STARTED.md`, `mise.toml`, `CLAUDE.md`
  - criteria: AC5
