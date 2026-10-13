Source Grafana admin login from OpenBao via ESO

## Why
The chart rendered Grafana's admin Secret from a committed placeholder (`CHANGE_ME_BEFORE_DEPLOY`) in a repo ArgoCD reads without credentials, so anyone on the LAN or tailnet could log in as admin if it was never changed.

## What changed
- New `templates/grafana-admin-secret.yaml`: ExternalSecret `grafana-admin` from OpenBao `secret/grafana` (`admin_user`, `admin_password`). Same pattern as Seafile and Tailscale.
- `values.yaml`: removed `adminPassword` and set `grafana.admin.existingSecret: grafana-admin`. The chart stops rendering its own Secret, and the Grafana container and its dashboard/datasource sidecars read `grafana-admin`.
- `application.yaml`: sync wave 4 → 6, so the ExternalSecret CRD (ESO, wave 5) exists on a fresh bootstrap.
- Docs: `secret/grafana` added to the OpenBao steps and the `vault-write` hint, a rotation runbook in `docs/GETTING-STARTED.md`, and `CLAUDE.md` secrets/waves updated.

## ⚠️ Before merging
Merging deploys: ArgoCD auto-syncs `main` (prune + self-heal), prunes `monitoring/prometheus-stack-grafana`, and rolls Grafana.
1. Write the key **first**. Otherwise the new Grafana pod waits on a missing Secret, though the old pod keeps serving:
   ```
   PW=$(openssl rand -base64 24)
   bao kv put secret/grafana admin_user=admin admin_password="$PW"
   ```
2. Merge, then check `kubectl -n monitoring get externalsecret grafana-admin` shows `SecretSynced`.
3. Grafana's database still holds the old password, so reset it:
   ```
   printf '%s' "$PW" | kubectl -n monitoring exec -i deploy/prometheus-stack-grafana -c grafana -- \
     grafana cli admin reset-admin-password --password-from-stdin
   ```
4. If the new pod is stuck on `Multi-Attach` (RWO volume on another node), delete the old Grafana pod.

## Acceptance criteria
- [x] AC1: ExternalSecret renders with the right store, keys and properties
- [x] AC2: Grafana and its sidecars read `grafana-admin`; no literal password rendered
- [x] AC3: no `change_me` placeholders under `kubernetes/`
- [x] AC4: wave 6 > ESO wave 5
- [x] AC5: docs and runbook updated

## How to verify
```
# render (needs helm + chart deps), then:
python3 -I specs/013-grafana-admin-secret/check_render.py rendered.yaml .
```
Rendered with helm v3.16.4 and kube-prometheus-stack 65.8.1: 11/11 checks pass (10 fail on `main`), and `helm lint` is clean.

## Follow-ups
- Grafana uses RollingUpdate with an RWO volume, so any rollout can stall on Multi-Attach (runbook covers it; consider `Recreate` once secrets are reliable).
- The ClusterSecretStore isn't namespace-scoped, so any namespace can read `secret/grafana` (#32).
- GETTING-STARTED Step 6 doesn't list `secret/seafile` (pre-existing).

Spec: `specs/013-grafana-admin-secret/spec.md` · Plan: `specs/013-grafana-admin-secret/plan.md`
Closes #13
