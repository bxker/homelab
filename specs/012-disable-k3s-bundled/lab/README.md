# Lab: disabling bundled Traefik/ServiceLB on a running k3s

Throwaway single-node k3s v1.36.5+k3s1 in the work sandbox (cgroup v1 VM, so the kubelet got
`--fail-cgroupv1=false` and containerd `restrict_oom_score_adj = true`; neither affects the result).
`argo-sim.yaml` stands in for ArgoCD-managed objects: a Middleware `basic-auth`, an IngressRoute using it,
and a LoadBalancer Service.

Before: 25 `traefik.io` CRDs, HelmCharts `traefik` + `traefik-crd`, IngressClass `traefik`, 2 svclb DaemonSets.

| Experiment | Steps | Result |
|---|---|---|
| 1. naive | restart with `--disable=traefik --disable=servicelb` | within 20 s: CRDs 25→0, Middleware 1→0, IngressRoute 1→0, IngressClass gone, svclb gone; `helm-delete-traefik` hangs on `helm uninstall --wait` |
| 2. protected | delete Secret `kube-system/sh.helm.release.v1.traefik-crd.v1`, then restart with disable | CRDs 25, Middleware 1, IngressRoute 1 kept; k3s traefik Deployment gone; svclb gone; IngressClass gone; uninstall hangs |
| 2 + finalizers | then `strip-servicelb-finalizers.sh` | `kube-system/traefik` Service deleted, HelmCharts 0, jobs 0; CRDs and CRs still kept |

Cause of the hang: ServiceLB's `service.kubernetes.io/load-balancer-cleanup` finalizer on every
LoadBalancer Service is never removed once ServiceLB is disabled.

## Playbook runs (the real `ansible/playbooks/tasks/k3s-disable-bundled.yml`)

From the pre-disable snapshot, with `/usr/local/bin/k3s` → the lab binary and a `systemctl` stub whose
`restart k3s` restarts the lab process (which then reads the written `/etc/rancher/k3s/config.yaml`).
Wrapper: `run-tasks.yml` (`k3s_ingressclass_wait_retries: 2`, since the lab has no ArgoCD).

| Run | Recap | Cluster after |
|---|---|---|
| 1 migrate | ok=14 changed=4 failed=0; 1 `systemctl restart k3s`; finalizer removed from `default/sim-lb`, `kube-system/traefik` | CRDs 25, Middleware 1, IngressRoute 1, HelmCharts 0, svclb 0, k3s traefik Deployment 0, no LB finalizers; IngressClass warning shown |
| 2 re-run | ok=6 changed=0, 0 `systemctl` calls | unchanged |
| 3 fresh node (`k3s_bin` missing, no config) | ok=5 changed=1 (config only), 0 `systemctl` calls | `config.yaml` identical to run 1's, root 0600 |
