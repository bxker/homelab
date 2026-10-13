# Plan: Pin the k3s version and keep the join token off command lines

Spec: [spec.md](spec.md) · Status: approved

## Callouts
- **New dependencies:** none (Renovate custom manager is config)
- **Public API / contract changes:** new inventory var `k3s_version`; the playbook now fails on version mismatch
- **Migrations / data changes:** none
- **Security triggers touched:** secrets (join token)
- **Domains:** scripting (Ansible), renovate config
- **Environments affected on deploy:** none on merge. The owner's next `mise run k3s-install` runs the
  version check, writes `/etc/rancher/k3s/config.yaml` on agents (same server/token they already use), and
  doesn't restart k3s.
- **Destructive or replacing changes:** none

## Approach
`ansible/inventory.yml` gets `k3s_version` under `all.vars`. A new first play on `k3s_cp:k3s_workers` stats
`/usr/local/bin/k3s`. Where it exists, the play reads `k3s --version` and asserts the pinned tag is in the
output (`any_errors_fatal`, so nothing changes anywhere on a mismatch). Both installs fetch `install.sh`
from `raw.githubusercontent.com/k3s-io/k3s/{{ k3s_version }}/` and set `INSTALL_K3S_VERSION`, keeping
`creates:`. Agents get `/etc/rancher/k3s/config.yaml` rendered with `to_nice_yaml` (root, 0600, `no_log`) and
install with `sh -s - agent`, so no `K3S_URL`/`K3S_TOKEN`. The token slurp/set_fact tasks become `no_log`.
Renovate gets a regex custom manager on `ansible/inventory.yml` (github-releases `k3s-io/k3s`, with a
versioning regex for the `+k3sN` build suffix).

## Files
| File | Change |
|---|---|
| `ansible/inventory.yml` | `k3s_version` var |
| `ansible/playbooks/k3s.yml` | version check play, pinned installs, agent config.yaml, no_log |
| `renovate.json` | custom manager for `k3s_version` |
| `CLAUDE.md` | provisioning note: version pin, check, upgrades are manual for now |

## Risks
- Provisional pin ≠ live → the next playbook run fails by design (AC6); the message names the fix.
- A Renovate bump merged without upgrading nodes → the check fails until the nodes are upgraded. CLAUDE.md says so.

## Test strategy
`check_k3s.py`: static assertions on the playbook (AC1–AC4), the Renovate regex run against the inventory
line (AC5, JS named groups converted for Python), and AC6 by rendering the assert's Jinja condition with
sample `k3s --version` outputs via the uvx ansible-core's Jinja. Plus `--syntax-check` and `ansible-lint`.

## Tasks
- [ ] **T1** [agent: implementer] Pin, version check, token via config.yaml
  - files: `ansible/inventory.yml`, `ansible/playbooks/k3s.yml`
  - criteria: AC1, AC2, AC3, AC4, AC6
  - review: each
- [ ] **T2** [agent: implementer] Renovate tracks k3s_version; doc note
  - files: `renovate.json`, `CLAUDE.md`
  - criteria: AC5
