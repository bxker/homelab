# Spec: Turn off k3s's bundled Traefik and ServiceLB without losing Traefik CRDs

Ticket: gh:12 · Size: standard · Status: approved

## Problem
k3s installs its own Traefik and ServiceLB next to the ArgoCD-managed Traefik and MetalLB: two ingress
controllers share the `traefik` IngressClass name and two LB controllers race on every LoadBalancer
Service. The obvious fix (`disable: [traefik, servicelb]` + restart) is dangerous on the running cluster,
as reproduced in a lab k3s v1.36.5 (`specs/012-disable-k3s-bundled/lab/`):
- k3s uninstalls its `traefik-crd` chart, whose CRDs are templates without `resource-policy: keep`, so all
  25 `traefik.io` CRDs and **every IngressRoute and Middleware** (incl. #46's logins) are deleted.
- The uninstall of k3s's Traefik then hangs, because ServiceLB's `load-balancer-cleanup` finalizer is never
  removed once ServiceLB is off. The same finalizer stays on every other LoadBalancer Service.

Tested safe sequence: delete the `traefik-crd` Helm release record → restart with `disable` → strip the
ServiceLB finalizers. Result: k3s Traefik + ServiceLB gone; CRDs, IngressRoutes, Middlewares kept.

## Goals
- New clusters never install the bundled Traefik/ServiceLB.
- The existing cluster migrates without deleting Traefik CRDs or the objects that use them.

## Non-goals
- Disabling other bundled components (local-storage, metrics-server). Upgrading k3s.

## Acceptance criteria
- **AC1**: Given a fresh install, then `/etc/rancher/k3s/config.yaml` with `disable: [traefik, servicelb]`
  exists on the server before k3s first starts.
- **AC2**: Given a server already running bundled Traefik, when the playbook runs, then before k3s restarts
  it removes every Helm release record of `traefik-crd` (so no CRD is uninstalled), and after the restart it
  removes ServiceLB's finalizer from every LoadBalancer Service and waits until no k3s Traefik HelmChart remains.
- **AC3**: Given the cluster is already migrated, when the playbook re-runs, then it restarts nothing and
  deletes nothing.
- **AC4**: Given the migration, then it waits (bounded) for IngressClass `traefik` to exist again (ArgoCD
  recreates it) and warns, without failing, if it doesn't.
- **AC5**: The sequence the playbook encodes is the one validated in the lab (CRDs 25 → 25,
  Middleware/IngressRoute kept, HelmCharts 2 → 0, svclb DaemonSets → 0), recorded in `lab/`.
- **AC6**: Docs say what the migration does, its brief API restart, and how to verify (MetalLB IPs, one IngressClass).

## Constraints
- k3s restart on the single control plane: API unavailable ~30 s; workloads keep running.
- The `traefik` IngressClass is deleted by k3s's chart uninstall; ArgoCD's selfHeal on the `traefik` app recreates it.

## Requirement changes
None.

## Open questions
None. Resolved at the Spec gate: (1) automate the migration in the playbook; (2) rely on ArgoCD selfHeal for
the `traefik` IngressClass, with a bounded wait and a warning (AC4).
