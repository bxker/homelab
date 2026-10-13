Make mise run all non-destructive; add confirmed rebuild

## Why
`mise run all` (via `cluster`) ran `tofu destroy -auto-approve` before provisioning, so every run wiped all VMs and every Longhorn volume (Seafile, MariaDB, OpenBao, Grafana) with no off-host backup, and `2>/dev/null || true` hid failures.

## What changed
- `all` and `cluster` never destroy. They're now ordered `run = [{ task = ... }]` steps. This also fixes a second bug: mise runs `depends` **in parallel**, so `all` used to start `cluster`, `gitops` and `configure` at the same time.
- `infra` saves a plan and applies it unattended only if nothing is deleted or replaced. Otherwise it shows a warning and needs a typed `yes`.
- `infra-destroy` / `destroy` no longer pass `-auto-approve`, so tofu asks for confirmation.
- New `mise run rebuild`: type the cluster name, then destroy → `cluster`.
- Tasks that prompt are `interactive = true` (mise only gives stdin to interactive/raw tasks).
- `terraform/tfplan` is gitignored and deleted on exit.
- Docs updated: `CLAUDE.md`, `README.md`, `docs/GETTING-STARTED.md`.

## Acceptance criteria
- [x] AC1: `all`/`cluster` never reach `tofu destroy`, verified by a task-graph check
- [x] AC2: no `-auto-approve` on any destroy
- [x] AC3: `rebuild` aborts (exit 1) unless the cluster name is typed
- [x] AC4: plans with deletes/replaces need a typed `yes`, verified with a stub `tofu`
- [x] AC5: no suppressed failures; docs updated

## How to verify
```
python3 -I specs/011-nondestructive-mise-all/verify_tasks.py .   # offline checks
mise tasks                     # rebuild listed
mise run infra                 # existing cluster: "No changes", nothing applied
mise run rebuild               # type a wrong name → "Aborted. Nothing was destroyed."
```
Not run against real mise/tofu in CI (neither is installed); please do the three manual checks above.

## Follow-ups
- Needs a recent mise (supports `{ task = ... }` steps and `interactive`).
- Backups before any rebuild: #19, #20.

Spec: `specs/011-nondestructive-mise-all/spec.md` · Plan: `specs/011-nondestructive-mise-all/plan.md`
Closes #11
