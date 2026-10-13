# Plan: Make `mise run all` non-destructive

Spec: [spec.md](spec.md) · Status: approved (small: one inline task, no Plan gate)

## Callouts
- **New dependencies:** none (POSIX sh + tofu only)
- **Public API / contract changes:** `mise run all`/`cluster` no longer rebuild from scratch; new `mise run rebuild`
- **Security triggers touched:** none
- **Domains:** scripting
- **Environments affected on deploy:** none until the owner runs a task
- **Destructive or replacing changes:** none

## Approach
`infra` saves a plan (`tofu plan -out`), inspects `tofu show -json` for any `"delete"` action
(covers destroy and replace), and applies the saved plan without asking only when there is none;
otherwise it asks for a typed `yes`. `infra-destroy` drops `-auto-approve` so tofu asks itself.
`rebuild` asks for the typed `$CLUSTER_NAME`, then runs `infra-destroy` → `cluster`.
mise runs `depends` in parallel and only gives stdin to `interactive`/`raw` tasks, so `all`,
`cluster`, `rebuild` use ordered `run = [{ task = … }]` steps and prompting tasks set
`interactive = true`. Inspection scripts use TOML literal strings (no escape surprises).

## Tasks
- [ ] **T1** [agent: engine/inline] Rework tasks in mise.toml; ignore saved plan file; update docs
  - files: `mise.toml`, `.gitignore`, `CLAUDE.md`, `README.md`, `docs/GETTING-STARTED.md`
  - criteria: AC1–AC5
