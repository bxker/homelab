Repo hygiene: drop .DS_Store, move Tailscale to infrastructure, fix stale docs

## Why
Three macOS `.DS_Store` files were committed, and several docs had drifted from the repo: the Tailscale values said to create its OAuth Secret by hand (OpenBao + ESO does it now), the README diagram and tree put Prometheus and Tailscale in the wrong group, the README Quick Start bypassed the `mise` tasks, and the MetalLB pool comment still listed `.203` (freed in #46). `argocd-ingress.yaml` was only applied by hand.

## What changed
- `.DS_Store` untracked (×3) and ignored.
- **Tailscale moved** `kubernetes/apps/workloads/tailscale` → `kubernetes/apps/infrastructure/tailscale` (`git mv`; only the Application's `path` changes). Its values comments describe the OpenBao flow.
- **README:** diagram/tree match `kubernetes/apps/` (incl. `ingress-auth`); Quick Start is the `mise` task sequence.
- **MetalLB** pool comment: pins are `.200` and `.201`.
- **`mise run gitops`** also applies `kubernetes/bootstrap/argocd-ingress.yaml`.
- `CLAUDE.md` Secrets item from the issue was already fixed in #44.

## Deploy impact
ArgoCD updates Application `tailscale`'s source path in place, since the Application name is unchanged. The chart files are byte-identical and the parsed values are equal, so the rendered resources don't change and nothing is pruned or recreated. Worth a glance after merge: `tailscale` should show Synced/Healthy with no resource changes.

## Acceptance criteria
- [x] AC1: no `.DS_Store` tracked; ignored
- [x] AC2: Tailscale comments describe OpenBao/ESO
- [x] AC3: move is a pure path change (rename similarity + parsed-values equality)
- [x] AC4: README matches the repo; Quick Start via `mise`
- [x] AC5: pool comment fixed
- [x] AC6: `gitops` applies the ArgoCD Ingress

## Follow-ups
- none

Spec: `specs/018-repo-hygiene/spec.md` · Plan: `specs/018-repo-hygiene/plan.md`
Closes #18
