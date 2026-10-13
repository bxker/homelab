# Spec: Source the Grafana admin password from OpenBao

Ticket: gh:13 · Size: standard · Status: draft

## Problem
Grafana's admin password is committed as `CHANGE_ME_BEFORE_DEPLOY` in a repo ArgoCD pulls
without credentials (public). If never overridden, anyone on the LAN or tailnet can log in
as admin at `grafana.homelab.local`. Seafile and Tailscale already get secrets from OpenBao
via ESO; Grafana should too, so no credential lives in Git.

## Goals
- No Grafana credential in the repo; the admin login comes from OpenBao `secret/grafana`.
- The owner has exact steps to rotate the live password so DB, Secret, and OpenBao agree.

## Non-goals
- SSO/OIDC for Grafana (#30). Scoping ESO access per namespace (#32). Rewriting Git history.

## Acceptance criteria
- **AC1**: Given the rendered `prometheus-stack` chart, then it contains an `ExternalSecret`
  (`external-secrets.io/v1`, store `openbao` ClusterSecretStore) producing Secret `grafana-admin`
  with keys `admin-user` and `admin-password` from `secret/grafana` properties `admin_user`, `admin_password`.
- **AC2**: Given the rendered chart, then the Grafana Deployment reads `GF_SECURITY_ADMIN_USER`/`_PASSWORD`
  from Secret `grafana-admin`, and the chart no longer renders its own admin Secret with a literal password.
- **AC3**: When running `grep -rniE "change_?me" kubernetes/`, then there are no matches.
- **AC4**: Given a fresh bootstrap, then the `ExternalSecret` CRD exists before prometheus-stack syncs (see OQ2).
- **AC5**: Given the docs, then `docs/GETTING-STARTED.md` (Step 6), `mise run vault-write` hints, and
  `CLAUDE.md` § Secrets list `secret/grafana`, and a rotation runbook explains the post-merge steps (OQ1).

## Constraints
- Grafana stores the admin password in its DB (PVC) after first start; the env var only seeds a
  new DB. Changing the Secret alone does **not** change the live password, and the chart's
  dashboard/datasource sidecars authenticate with the Secret's values, so a mismatch breaks reloads.
- Cluster mutations (OpenBao writes, password reset in the pod) are the owner's, not this run's.

## Requirement changes
None.

## Open questions
1. **Rotation procedure.** Recommended: owner writes `secret/grafana` *before* merging; after merge and
   ESO sync, runs `kubectl -n monitoring exec deploy/<grafana> -c grafana -- grafana cli admin
   reset-admin-password "$PW"` with the same value. Documented as a runbook, not automated. *Why: the
   Secret alone doesn't change the DB password (Constraints).*
2. **Sync ordering.** prometheus-stack is wave 4, ESO wave 5, so on a fresh cluster the ExternalSecret
   CRD doesn't exist yet and the app's sync fails (child apps have no retry, #24). Recommended: move
   prometheus-stack to wave 6. *Why: AC4; alternative is to wait for #24.*
3. **Validation tooling.** `helm` isn't installed here. Recommended: allow downloading a pinned helm
   binary into the scratchpad (not the repo) to render the chart for AC1/AC2 evidence. Without it,
   evidence for AC1/AC2 is static review of templates/values only.
