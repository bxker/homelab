# Retro: 018-repo-hygiene

Ticket: gh:18 · Size: standard · PR: https://github.com/bxker/homelab/pull/48

## Metrics
| Metric | Value |
|---|---|
| Duration (intake → deliver) | ~0:08 agent time, plus gate waits |
| Gate rework (spec / plan / deliver) | 0 / 0 / 0 |
| Tasks | 3 (fallback mode, sequential) |
| Review first-pass rate | 2/2 |
| Retries | 0 |
| Interventions | 0 |
| Criteria passed | 6/6 |

## Reflections
1. skipped
2. skipped
3. skipped

## Proposed improvements
- When a chart's Helm repo is unreachable, a pure `git mv` plus parsed-values equality is enough
  evidence that a path move changes no rendered resources. Record this as an accepted technique.
- Python edits to JSON reformat the whole file; edit the text instead to keep diffs minimal (seen in #16).
