# Retro: 014-admin-ui-auth

Ticket: gh:14 · Size: standard · PR: https://github.com/bxker/homelab/pull/46

## Metrics
| Metric | Value |
|---|---|
| Duration (intake → deliver) | ~0:10 agent time, plus gate waits |
| Time per stage | spec ~2m (incl. Traefik source checks), plan ~1m, implement ~4m, verify ~1m |
| Gate rework (spec / plan / deliver) | 0 / 0 / 0 |
| Tasks | 4 (fallback mode, sequential) |
| Review first-pass rate | 4/4 |
| Retries | 0 (T4's TOML escape bug was caught by its own check before commit) |
| Interventions | 0 |
| Criteria passed | 5/5 (offline; live 401s and fail-closed behaviour left to owner) |

## Reflections
1. skipped
2. skipped
3. skipped

## Proposed improvements
- analyst: check rendered entrypoints/Service ports before calling a route "exposed". The original review
  overstated the Traefik dashboard's exposure.
- `kubernetes` skill: with GitOps sync waves, an `ExternalSecret` can't live in an app that syncs before
  ESO. Put it in a later-wave app (pattern used here and in #13).
- `scripting` skill: inside TOML basic strings, `\$` is an invalid escape. Prefer single-quoted shell
  strings in mise tasks, and always run a TOML parse after editing mise.toml.
