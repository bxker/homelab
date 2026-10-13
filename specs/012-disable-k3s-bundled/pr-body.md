Disable k3s's bundled Traefik and ServiceLB without losing Traefik CRDs

## Why
k3s installs its own Traefik and ServiceLB next to the ArgoCD-managed Traefik and MetalLB: two ingress controllers on the `traefik` IngressClass, and two controllers racing on every LoadBalancer Service.

**The obvious fix is destructive on a running cluster.** I reproduced it on a throwaway k3s v1.36.5. Setting `disable: [traefik, servicelb]` and restarting makes k3s uninstall its `traefik-crd` chart, whose CRDs aren't marked to be kept. Within 20 seconds all 25 `traefik.io` CRDs were gone, and with them **every IngressRoute and Middleware**, including #46's logins. The uninstall of k3s's Traefik then hangs forever on ServiceLB's finalizer.

## What changed
New `ansible/playbooks/tasks/k3s-disable-bundled.yml`, run by the server play before install:
- **Fresh node:** writes `/etc/rancher/k3s/config.yaml` (`disable: [traefik, servicelb]`, root 0600) before k3s first starts.
- **Node still running the bundled Traefik**, one time:
  1. delete the `traefik-crd` Helm release record, so its uninstall keeps the CRDs;
  2. restart k3s and wait for `/readyz`;
  3. strip ServiceLB's `load-balancer-cleanup` finalizer from each LoadBalancer Service;
  4. wait for the uninstall to finish;
  5. wait up to 5 min for ArgoCD to restore the `traefik` IngressClass, warning (not failing) if it doesn't.
- **Already migrated:** nothing happens.

Docs: a migration section with verification commands in `docs/GETTING-STARTED.md`, and a `CLAUDE.md` note.

## ⚠️ What your next `mise run k3s-install` does
- k3s API restart, ~30 s. Pods keep running.
- k3s's Traefik and ServiceLB are uninstalled. **Traefik CRDs, IngressRoutes and Middlewares stay.**
- The shared `traefik` IngressClass is deleted by k3s's uninstall, and ArgoCD's self-heal recreates it. Plain Ingresses (Longhorn, Grafana, Seafile, AdGuard, OpenBao) aren't routed until it's back. If the playbook warns, sync the `traefik` app.
- Afterwards, run the checks in GETTING-STARTED: no k3s HelmCharts, no `svclb` DaemonSets, one IngressClass, LoadBalancer IPs from MetalLB.

Merging changes nothing on the cluster by itself.

## Acceptance criteria
- [x] AC1: fresh nodes never install bundled Traefik/ServiceLB
- [x] AC2: migration keeps CRDs, strips finalizers, waits for the uninstall
- [x] AC3: re-run is a no-op
- [x] AC4: bounded IngressClass wait with a warning
- [x] AC5: encodes the lab-tested sequence
- [x] AC6: docs

## How it was tested
The real task file was run against a throwaway k3s v1.36.5, from a snapshot with the bundled Traefik installed plus stand-in Middleware, IngressRoute and LoadBalancer Service (`specs/012-disable-k3s-bundled/lab/`):

| Run | Result |
|---|---|
| migrate | CRDs 25 → 25, Middleware and IngressRoute kept, HelmCharts 2 → 0, svclb 2 → 0, finalizers removed |
| re-run | changed=0, no restart |
| fresh node | only `config.yaml` written |

For comparison, the naive disable gave CRDs 25 → 0 with the CRs deleted. `ansible-lint` passes the production profile.

## Follow-ups
- none

Spec: `specs/012-disable-k3s-bundled/spec.md` · Plan: `specs/012-disable-k3s-bundled/plan.md`
Closes #12
