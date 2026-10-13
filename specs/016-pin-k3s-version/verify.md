# Verify: Pin the k3s version and keep the join token off command lines

Run at 2026-10-13T03:53:41Z on commit `2f03370`.

## Checks
| Check | Command | Result |
|---|---|---|
| Tests | none in repo | not configured |
| Syntax | `uvx --from ansible-core ansible-playbook --syntax-check -i ansible/inventory.yml ansible/playbooks/k3s.yml` | pass |
| Lint | `uvx ansible-lint ansible/playbooks/k3s.yml` | pass, production profile (baseline: 4 failures: curl-in-shell, missing pipefail ×2 each) |
| Static assertions | `python3 specs/016-pin-k3s-version/check_k3s.py .` (PyYAML) | pass: 14/14 (baseline: 10 fail) |
| Version check (live run) | first play run locally (`connection: local`) against a fake `/usr/local/bin/k3s` | absent → skipped; v1.36.5 → ok; v1.33.5 → fails on every host with the fix message |
| Token file | agent `config.yaml` rendered with a sample `K10…::server:…` token | valid YAML, mode 600 |
| Plan / diff | — | offline only |

## Acceptance criteria
| Criterion | Evidence | Result |
|---|---|---|
| AC1 | `k3s_version` once in inventory `all.vars`; both installs `environment.INSTALL_K3S_VERSION: "{{ k3s_version }}"` | pass |
| AC2 | No `get.k3s.io`; `get_url` from `raw.githubusercontent.com/k3s-io/k3s/{{ k3s_version }}/install.sh` | pass |
| AC3 | No command/env contains the token; agents' `config.yaml` root 0600 `no_log`; slurp + set_fact `no_log` | pass |
| AC4 | Both installs keep `creates: /usr/local/bin/k3s` | pass |
| AC5 | Renovate regex manager: file pattern matches `ansible/inventory.yml`, captures `v1.36.5+k3s1`, versioning regex parses it | pass |
| AC6 | Local run of the check play (above) | pass |

## Notes
- `proxmox.yml` fails `--syntax-check` under bare ansible-core (needs the `ansible.posix` collection). It's unchanged by this PR and fails the same way on `main`.
- The pinned `v1.36.5+k3s1` is provisional. The live version isn't recorded anywhere, and the next playbook run reports it.
