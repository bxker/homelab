# Spec: Make `mise run all` non-destructive

Ticket: gh:11 · Size: small · Status: draft

## Problem
`mise run all` (and `mise run cluster`) silently runs `tofu destroy -auto-approve` before
provisioning, wiping every VM and all Longhorn data (Seafile, MariaDB, OpenBao, Grafana).
There are no off-host backups, so one habitual "deploy" command causes unrecoverable loss.
Destroy failures are also hidden by `2>/dev/null || true`.

## Goals
- Deploy commands (`all`, `cluster`, `infra`) never destroy or replace VMs without a human typing a confirmation.
- Destroying stays possible, but only through explicit, confirmed tasks.

## Non-goals
- Backups (Phase 1, #19/#20). Changing Terraform resources themselves.

## Acceptance criteria
- **AC1**: Given an existing cluster, when `mise run all` or `mise run cluster` runs, then no task in its chain invokes `tofu destroy`.
- **AC2**: When `mise run infra-destroy` or `mise run destroy` runs, then the destroy only proceeds after an interactive confirmation (no `-auto-approve` on any destroy).
- **AC3**: A new `mise run rebuild` destroys and re-provisions (infra → k3s-install) only after the user types the cluster name (`$CLUSTER_NAME`); a mismatch aborts with non-zero exit and nothing destroyed.
- **AC4**: `mise run infra` does not auto-apply a plan that deletes or replaces any resource; such a plan requires interactive approval (see OQ1).
- **AC5**: No destroy-related failure is suppressed (`2>/dev/null || true` removed); `CLAUDE.md`, `README.md`, and `docs/GETTING-STARTED.md` describe `all` as non-destructive and document `rebuild`.

## Constraints
- mise, tofu not installed in this environment: evidence is offline (TOML parse, `bash -n` on every task script, grep of the task graph). Live run is the owner's manual check.
- Typed-name prompt must work from bash in mise's `run` scripts (no new dependencies).

## Requirement changes
None.

## Open questions
1. **AC4 approach** — *`tofu apply -auto-approve` can also replace VMs (e.g. a changed disk/image forces replacement)*. Options: (a) `infra` runs `tofu plan -out`, auto-applies only if the plan has zero deletes/replaces, otherwise prompts (recommended: `all` stays hands-off for the normal case); (b) drop `-auto-approve` from apply entirely (simplest, but `mise run all` always stops for "yes"); (c) leave apply as is (out of scope).
