# Retro: 012-disable-k3s-bundled

Ticket: gh:12 · Size: standard · PR: https://github.com/bxker/homelab/pull/49

## Metrics
| Metric | Value |
|---|---|
| Duration (intake → deliver) | ~0:30 agent time (most of it building and running the k3s lab), plus gate waits |
| Gate rework (spec / plan / deliver) | 0 / 0 / 0 |
| Tasks | 2 (fallback mode, sequential) |
| Review first-pass rate | 2/2 |
| Retries | 0 (lint `no-handler` ×4 fixed before commit) |
| Interventions | 0 |
| Criteria passed | 6/6 (lab-tested; owner's cluster untouched) |

## Reflections
1. skipped
2. skipped
3. skipped

## Proposed improvements
- The ticket's own fix (plain `disable` + restart) would have deleted every Traefik CR on the live
  cluster. analyst/architect: for changes that make a controller uninstall something, check what the
  uninstall removes (chart templates vs `crds/`, `resource-policy: keep`) before planning.
- A throwaway k3s in the sandbox was decisive and cheap. Record the workarounds (cgroup v1 kubelet
  flag, containerd `restrict_oom_score_adj`) in the `kubernetes` skill as a "local lab" recipe.
- Never `pkill -f <pattern>` in a command whose own text contains the pattern. It killed the shell once here.
