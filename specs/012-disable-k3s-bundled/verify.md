# Verify: Turn off k3s's bundled Traefik and ServiceLB without losing Traefik CRDs

Run at 2026-10-13T04:34:43Z on commit `0962679`.

## Checks
| Check | Command | Result |
|---|---|---|
| Syntax | `uvx --from ansible-core ansible-playbook --syntax-check -i ansible/inventory.yml ansible/playbooks/k3s.yml` | pass |
| Lint | `uvx ansible-lint ansible/playbooks/k3s.yml ansible/playbooks/tasks/k3s-disable-bundled.yml` | pass, production profile |
| Regression | #16 `check_k3s.py`, #11 `verify_tasks.py` | pass |
| Lab | real task file vs throwaway k3s v1.36.5 (`lab/README.md`) | 3 runs pass |
| Plan / diff | owner's cluster | not touched |

## Acceptance criteria
| Criterion | Evidence | Result |
|---|---|---|
| AC1 | Lab run 3 (no k3s binary): only `config.yaml` written (root 0600, `disable: [traefik, servicelb]`), 0 restarts; task runs before "Install k3s server" | pass |
| AC2 | Lab run 1: traefik-crd release Secret deleted before `systemctl restart k3s`; finalizer removed from both LB Services; HelmCharts 2 → 0 | pass |
| AC3 | Lab run 2: changed=0, 0 `systemctl` calls | pass |
| AC4 | Lab run 1: IngressClass wait ran (2 retries in lab), warning printed, play didn't fail | pass |
| AC5 | Lab run 1: CRDs 25 → 25, Middleware 1 → 1, IngressRoute 1 → 1, svclb 2 → 0 (vs naive experiment: CRDs 25 → 0, CRs deleted) | pass |
| AC6 | GETTING-STARTED migration section + checks; CLAUDE.md note | pass |

## Notes
- Lab differs from the real nodes only in sandbox workarounds (cgroup v1 kubelet flag, containerd OOM restriction) and a `systemctl` stub; k3s version matches the pin.
- ArgoCD restoring the IngressClass wasn't observable in the lab (no ArgoCD); the playbook waits and warns.
