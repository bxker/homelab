# Plan: Repo hygiene: macOS cruft, stale docs, Tailscale location

Spec: [spec.md](spec.md) · Status: approved

## Callouts
- **New dependencies:** none
- **Public API / contract changes:** app path `workloads/tailscale` → `infrastructure/tailscale`; `mise run gitops` also applies the ArgoCD Ingress
- **Migrations / data changes:** none
- **Security triggers touched:** none
- **Domains:** gitops, kubernetes, docs
- **Environments affected on deploy:** ArgoCD updates Application `tailscale`'s `spec.source.path` in place; rendered manifests unchanged → no resource changes
- **Destructive or replacing changes:** none

## Approach
`git rm --cached` the three `.DS_Store` and add `.DS_Store` to `.gitignore`. `git mv` the Tailscale chart
directory (so Git records a 100% rename) and change only `application.yaml`'s `path`; rewrite the values
comment block. Evidence for "nothing changes in the cluster": rename similarity plus a before/after render
of the chart if its Helm repo is reachable, otherwise a byte-diff of every chart file. README: fix the
diagram groups, the tree (`ingress-auth`, `tailscale` under infrastructure), and make Quick Start the
`mise` task sequence. Fix the pool comment. Add `kubectl apply -f kubernetes/bootstrap/argocd-ingress.yaml`
to the `gitops` task after the app-of-apps apply.

## Tasks
- [ ] **T1** [agent: implementer] Remove `.DS_Store`, ignore it
  - files: `.gitignore`, `.DS_Store`, `kubernetes/.DS_Store`, `kubernetes/apps/.DS_Store`
  - criteria: AC1
- [ ] **T2** [agent: implementer] Move Tailscale to infrastructure; fix its comments
  - files: `kubernetes/apps/workloads/tailscale/**`, `kubernetes/apps/infrastructure/tailscale/**`
  - criteria: AC2, AC3
  - review: each
- [ ] **T3** [agent: implementer] README, pool comment, gitops task
  - files: `README.md`, `kubernetes/apps/infrastructure/metallb/templates/pool.yaml`, `mise.toml`
  - criteria: AC4, AC5, AC6
