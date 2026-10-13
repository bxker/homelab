# Verify: Repo hygiene: macOS cruft, stale docs, Tailscale location

Run at 2026-10-13T04:01:06Z on commit `901c6f1`.

## Checks
| Check | Command | Result |
|---|---|---|
| Tests | none in repo | not configured |
| TOML / tasks | `tomllib` parse; #11 `verify_tasks.py` | pass |
| Render | Tailscale Helm repo unreachable from here | not run; input identity shown instead (AC3) |

## Acceptance criteria
| Criterion | Evidence | Result |
|---|---|---|
| AC1 | `git ls-files \| grep -c DS_Store` → 0; `git check-ignore .DS_Store` → ignored | pass |
| AC2 | `kubectl create secret` → 0 matches; comments describe `secret/tailscale` → ESO → `operator-oauth` | pass |
| AC3 | `git diff -M`: Chart.yaml + 3 templates are 0-line renames; parsed values identical; Application identical except `spec.source.path`, name `tailscale` | pass |
| AC4 | README tree lists all 11 apps under the right group; diagram regrouped; Quick Start has no `kubectl` | pass |
| AC5 | `pool.yaml` mentions `.203` 0 times | pass |
| AC6 | `gitops` task runs `kubectl apply -f kubernetes/bootstrap/argocd-ingress.yaml` | pass |

## Notes
- ArgoCD behaviour on the path change (in-place update, no prune) follows from Application identity by name; not observed live.
