# Retro: 011-nondestructive-mise-all

Ticket: gh:11 · Size: small · PR: https://github.com/bxker/homelab/pull/43

## Metrics
| Metric | Value |
|---|---|
| Duration (intake → deliver) | ~1:00 wall clock, mostly waiting at the Spec and Deliver gates plus two worker restarts |
| Time per stage | spec ~1m, implement ~10m, verify ~2m (agent time) |
| Gate rework (spec / plan / deliver) | 0 / skipped / 0 |
| Tasks | 1 (inline, no waves) |
| Review first-pass rate | 1/1 (inline self-review) |
| Retries | 0 |
| Interventions | 0 |
| Criteria passed | 5/5 (offline; live mise/tofu check left to owner) |

## Reflections
1. skipped
2. skipped
3. skipped

## Proposed improvements
- `project-commands`: when a repo has no tests and the toolchain (mise, tofu) is missing, suggest a
  stub-binary behaviour check like `verify_tasks.py` as the default evidence for task-runner changes.
- `scripting` domain: add a checklist item: "prompts in task runners need stdin (mise: `interactive`/`raw`;
  `depends` run in parallel)". That parallel-depends bug was found only by reading the mise docs.
- The verify script's first run flagged a false positive (matching "destroys" in a comment). Prefer
  matching commands (`tofu destroy`) over bare words in graph checks.
