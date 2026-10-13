# Retro: 016-pin-k3s-version

Ticket: gh:16 · Size: standard · PR: https://github.com/bxker/homelab/pull/47

## Metrics
| Metric | Value |
|---|---|
| Duration (intake → deliver) | ~0:15 agent time, plus gate waits |
| Time per stage | spec ~3m (incl. a revision), plan ~2m, implement ~8m, verify ~1m |
| Gate rework (spec / plan / deliver) | 1 / 0 / 0 (owner couldn't supply the live version → AC6 added) |
| Tasks | 2 (fallback mode, sequential) |
| Review first-pass rate | 2/2 (one MEDIUM fixed in-task: stale install.sh on bump) |
| Retries | 0 |
| Interventions | 1 (out-of-scope commit restoring #14/#15 plans, approved at Deliver) |
| Criteria passed | 6/6 |

## Reflections
1. skipped
2. skipped
3. skipped

## Proposed improvements
- Engine: never write a file with `open(p, 'w').write(open(p).read()...)`, because it truncates before it reads.
  That emptied two merged plans (#14, #15). Read into a variable first.
- analyst: when a live value can't be obtained, prefer a guard that detects and reports the mismatch over
  a silent guess (worked well here).
- Check scripts: select tasks by exact name prefix, and accept both `args:` and module-level parameters.
  Two false failures came from loose matching.
