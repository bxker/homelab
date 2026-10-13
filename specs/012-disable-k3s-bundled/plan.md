# Plan: Turn off k3s's bundled Traefik and ServiceLB without losing Traefik CRDs

Spec: [spec.md](spec.md) · Status: draft

## Callouts
- **New dependencies:** none
- **Public API / contract changes:** new server file `/etc/rancher/k3s/config.yaml` (`disable: [traefik, servicelb]`)
- **Migrations / data changes:** one-time, on the owner's next `mise run k3s-install`: deletes the
  `traefik-crd` Helm release Secret(s), restarts k3s (API down ~30 s), strips ServiceLB finalizers
- **Security triggers touched:** none
- **Domains:** scripting (Ansible), kubernetes
- **Environments affected on deploy:** none on merge; the playbook run migrates the cluster
- **Destructive or replacing changes:** k3s's bundled Traefik and ServiceLB are uninstalled (intended);
  the shared `traefik` IngressClass is deleted by that uninstall and recreated by ArgoCD

## Approach
New task file `ansible/playbooks/tasks/k3s-disable-bundled.yml`, included by the server play before
"Install k3s server". For a fresh node it only writes `config.yaml`. For a node running k3s:
1. Detect bundled HelmCharts `traefik`/`traefik-crd` in `kube-system`.
2. If present, delete Secrets `-l owner=helm,name=traefik-crd` (no CRD gets uninstalled).
3. Write `config.yaml` (root, 0600).
4. If it changed or bundled charts exist, restart `k3s` (systemd) and wait for `/readyz`.
5. Strip only the `service.kubernetes.io/load-balancer-cleanup` finalizer from each LoadBalancer Service
   (merge patch with the rest of the list).
6. Wait until both HelmCharts are gone (fail after ~5 min).
7. Wait up to `k3s_ingressclass_wait_retries` × 10 s for IngressClass `traefik`; warn if still missing.
`kubectl` calls go through `{{ k3s_bin }} kubectl` (default `/usr/local/bin/k3s`).

## Files
| File | Change |
|---|---|
| `ansible/playbooks/tasks/k3s-disable-bundled.yml` | new: steps above |
| `ansible/playbooks/k3s.yml` | include it in the server play before install |
| `CLAUDE.md`, `docs/GETTING-STARTED.md` | what the migration does, how to verify |

## Risks
- Restart while ArgoCD/MetalLB are busy → brief API outage only; mitigated by `/readyz` wait.
- An unknown third chart sharing names → guarded by exact label selector `name=traefik-crd`.

## Test strategy
Run the real task file against the lab k3s (restored pre-disable snapshot), with `/usr/local/bin/k3s` and
`/etc/rancher/k3s/*` pointing at the lab and a `systemctl` shim whose `restart k3s` restarts the lab
process (which then reads the written `config.yaml`). Expect: CRDs 25, Middleware/IngressRoute kept,
HelmCharts 0, svclb 0, finalizers stripped, IngressClass warning (no ArgoCD in the lab). Run it again →
no changes, no restart (AC3). Fresh path: run with no k3s binary → only `config.yaml` written.
Plus syntax-check and ansible-lint.

## Tasks
- [ ] **T1** [agent: implementer] Task file + include
  - files: `ansible/playbooks/tasks/k3s-disable-bundled.yml`, `ansible/playbooks/k3s.yml`
  - criteria: AC1, AC2, AC3, AC4, AC5
  - review: each
- [ ] **T2** [agent: implementer] Docs
  - files: `CLAUDE.md`, `docs/GETTING-STARTED.md`
  - criteria: AC6
