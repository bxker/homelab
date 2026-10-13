# Retro: 017-longhorn-prereqs

Ticket: gh:17 · Size: standard · PR: https://github.com/bxker/homelab/pull/50

## Metrics
| Metric | Value |
|---|---|
| Duration (intake → deliver) | ~0:15 agent time, plus gate waits and two worker restarts |
| Gate rework (spec / plan / deliver) | 0 / 0 / 0 |
| Tasks | 2 (fallback mode, sequential) |
| Review first-pass rate | 2/2 |
| Retries | 0 (two harness fixes in the sandbox run: interpreter, then Ubuntu's python3.12) |
| Interventions | 0 |
| Criteria passed | 5/5 (AC3 with a modprobe-stub caveat) |

## Reflections
1. skipped
2. skipped
3. skipped

## Proposed improvements
- Local Ansible runs: always pass the target OS's own interpreter (`/usr/bin/python3.12` here), since
  apt needs `python3-apt` built for it.
- When two open PRs edit the same doc, pick separate anchors and prove it with `git merge-tree` before pushing.
- The PR-create call can time out yet do nothing: list PRs by head branch before retrying (done here).
