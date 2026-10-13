# Verify: Make `mise run all` non-destructive

Run at 2026-10-13T01:52:30Z on commit `a272ba6`.

## Checks
| Check | Command | Result |
|---|---|---|
| Tests | none in repo | not configured |
| Validate (TOML) | `tomllib.load(mise.toml)` | pass |
| Validate (scripts) | `sh -n -c <script>` for all 18 inline scripts | pass |
| Behaviour | `python3 -I specs/011-nondestructive-mise-all/verify_tasks.py .` (stub `tofu`) | pass |
| Plan / diff | — | offline only (mise, tofu not installed here) |

## Acceptance criteria
| Criterion | Evidence | Result |
|---|---|---|
| AC1 | Task graph from `all`/`cluster`/`infra` reaches `cluster, configure, gitops, infra, k3s-install`; none run `tofu destroy` | pass |
| AC2 | Only `tofu destroy` is in `infra-destroy`, without `-auto-approve`; `destroy` runs it as a step; task is `interactive` | pass |
| AC3 | `rebuild` prompt: `homelab` → rc 0; `nope` / empty → rc 1 before any destroy step; steps after prompt = `infra-destroy, cluster` | pass |
| AC4 | Stub plans: `create`/`no-op`/`update` auto-apply; `delete,create`, `create,delete` with no/blank answer → rc 1, not applied; `delete` + `yes` → applied; `tfplan` removed every time | pass |
| AC5 | No `\|\| true` in any task; CLAUDE.md, README.md, GETTING-STARTED.md describe `all` as non-destructive and document `rebuild` | pass |

## Notes
- Not run against real mise/tofu. Owner check before merge: `mise tasks` lists `rebuild`; `mise run infra` on the
  existing cluster shows "No changes" and applies nothing; `mise run rebuild` then typing a wrong name aborts.
- Requires a mise recent enough to support `{ task = "..." }` steps in `run` and `interactive = true`.
