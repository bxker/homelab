# Verify: Source the Grafana admin password from OpenBao

Run at 2026-10-13T02:29:42Z on commit `71274a5`.

## Checks
| Check | Command | Result |
|---|---|---|
| Tests | none in repo | not configured |
| Render | helm v3.16.4 (built from source) `template` with vendored kube-prometheus-stack 65.8.1 (newest 65.x on GitHub releases) | pass |
| Lint | `helm lint` | pass: 1 linted, 0 failed |
| Render assertions | `python3 -I specs/013-grafana-admin-secret/check_render.py <rendered> .` | pass: 11/11 (baseline: 10 fail) |
| TOML | `tomllib.load(mise.toml)`; #11 `verify_tasks.py` | pass |
| Plan / diff | — | offline only (no cluster access) |

## Acceptance criteria
| Criterion | Evidence | Result |
|---|---|---|
| AC1 | Render: ExternalSecret `grafana-admin`, `external-secrets.io/v1`, store `openbao`/ClusterSecretStore, `admin-user`←`grafana.admin_user`, `admin-password`←`grafana.admin_password` | pass |
| AC2 | Render: `GF_SECURITY_ADMIN_USER/PASSWORD` and 4 sidecar `REQ_*` creds → `grafana-admin`; chart Secret `prometheus-stack-grafana` (placeholder literal) no longer rendered | pass |
| AC3 | `grep -rniE "change_?me" kubernetes/` → no matches | pass |
| AC4 | prometheus-stack wave 6 > external-secrets wave 5 | pass |
| AC5 | `secret/grafana` in GETTING-STARTED (3), mise.toml (1), CLAUDE.md (1); rotation runbook with `reset-admin-password --password-from-stdin` (flag confirmed in Grafana v11.3.0 source) | pass |

## Notes
- ArgoCD resolves `65.*` from the Helm repo index, which this environment can't reach; 65.8.1 is the newest 65.x release asset on GitHub (65.8.2/65.9.0/65.10.0 → 404).
- Not checked live: ESO sync, Grafana rollout, password reset. See the Deliver checklist.
