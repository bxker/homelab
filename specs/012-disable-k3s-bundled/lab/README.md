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
