# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Stack

Proxmox VE (bare metal) → 3 Ubuntu 24.04 VMs via Terraform (cloud-init) → k3s via Ansible → ArgoCD GitOps.

IPs configured in `mise.toml` env vars and `terraform.tfvars` (both gitignored or loaded from `.env`).

## Common Commands

All tasks run through `mise`:

```bash
mise run all            # full deploy, non-destructive: cluster (provision+k3s) → gitops → configure
mise run infra          # tofu apply; asks first if the plan destroys/replaces anything
mise run rebuild        # DESTROY all VMs + data, then cluster (asks for cluster name)
mise run k3s-install    # ansible: install k3s, write ~/.kube/homelab.yaml
mise run gitops         # install ArgoCD + apply app-of-apps
mise run configure      # ansible: harden Proxmox host
mise run sync           # apply app-of-apps to existing cluster (not a full gitops reinstall)
mise run status         # kubectl get nodes + ArgoCD apps + LB services
mise run deps           # helm dependency build for all wrapper charts
mise run destroy        # tofu destroy (tofu asks for confirmation)
```

Manual Helm operations (local preview only — ArgoCD deploys for real):

```bash
cd kubernetes/apps/infrastructure/metallb
helm dependency build
helm template metallb . --namespace metallb-system
```

## Architecture

### Provisioning Flow

1. **Terraform** (`terraform/k3s-vms.tf`) — downloads Ubuntu 24.04 cloud image via `proxmox_virtual_environment_download_file`, creates 3 VMs with static IPs and SSH key injected via cloud-init. Provider: `bpg/proxmox ~0.66`.

2. **Ansible** (`ansible/playbooks/k3s.yml`) — installs k3s on control plane (`--cluster-init`), joins workers via node token, patches kubeconfig server address from `127.0.0.1` to the CP IP, writes `~/.kube/homelab.yaml` (never `~/.kube/config`; `mise.toml` sets `KUBECONFIG` to it). SSH uses trust-on-first-use host keys in `ansible/known_hosts` (gitignored); `mise run infra-destroy` clears them. Every node installs `k3s_version` from `ansible/inventory.yml` (Renovate proposes bumps). The playbook never upgrades a node: its first play stops if an installed node runs a different version, so upgrade the nodes before merging a bump. Workers read the join token from `/etc/rancher/k3s/config.yaml` (0600), never from a command line. The server's `/etc/rancher/k3s/config.yaml` disables k3s's bundled Traefik and ServiceLB and exposes controller-manager (10257), scheduler (10259) and etcd (2381) metrics for Prometheus (`tasks/k3s-disable-bundled.yml`); changing it restarts k3s. On a server that still runs them, the playbook migrates once, keeping the `traefik.io` CRDs (see `docs/GETTING-STARTED.md`).

3. **ArgoCD** bootstrapped manually once via `mise run gitops` — applies the upstream v2.13.3 install manifest, then `kubernetes/bootstrap/argocd-install.yaml` (ConfigMap setting `server.insecure: "true"`). After bootstrap, ArgoCD self-manages everything. `kubernetes/bootstrap/argocd-ingress.yaml` adds a Traefik Ingress at `argocd.homelab.local` once Traefik is synced.

### GitOps Structure

`kubernetes/apps/app-of-apps.yaml` — root ArgoCD Application. Recurses `kubernetes/apps/` looking for `application.yaml` files. Every app auto-deploys when committed.

Each app is a **wrapper Helm chart**:
```
kubernetes/apps/<infrastructure|workloads>/<app>/
├── Chart.yaml        # declares upstream chart as dependency, pins version
├── values.yaml       # overrides nested under the dependency name as key
├── application.yaml  # ArgoCD Application pointing to this directory
└── templates/        # optional: extra K8s resources (Ingress, CRDs, Secrets)
```

Values for the upstream subchart **must** be nested under the dependency name:
```yaml
# Chart.yaml: dependency name: metallb
metallb:
  speaker:
    frr:
      enabled: false
```

Top-level keys in `values.yaml` go to your `templates/`, not the subchart.

ArgoCD runs `helm dependency build` automatically. Never commit the `charts/` directory.

### Sync Waves

All apps use `argocd.argoproj.io/sync-wave` annotations in `application.yaml` to control ordering. Approximate wave assignments: MetalLB (1) → Traefik / cert-manager / AdGuard Home (2) → Longhorn (3) → OpenBao (4) → External Secrets Operator (5) → Prometheus Stack / Tailscale / Ingress auth (6) → Seafile (10).

### Adding a New App

1. Create `kubernetes/apps/workloads/<app>/` with `Chart.yaml`, `values.yaml`, `application.yaml`
2. Copy `application.yaml` from an existing app; update `name`, `path`, `namespace`
3. Test locally: `helm dependency build && helm template <app> .`
4. Commit and push — ArgoCD picks it up automatically

Update `repoURL` in `app-of-apps.yaml` and all `application.yaml` files to your actual Git remote before first deploy.

### GitHub Actions

`.github/workflows/renovate-approve.yml` — auto-approves pull requests opened by the Renovate bot. Renovate is configured via `renovate.json` to watch `kubernetes/**/Chart.yaml` for upstream chart version bumps.

### Terraform Notes

`terraform.tfvars` (gitignored) requires `ssh_public_key` — your workstation's public key for SSH access to Ubuntu VMs. Use `local-zfs` for `storage_pool` if Proxmox was installed with ZFS.

### Secrets

Secrets are kept out of Git:
- **`.env`** (gitignored) — Proxmox URL, API token, node name. Loaded by mise via `_.file = ".env"`. See `.env.example` for the template.
- **`terraform.tfvars`** (gitignored) — SSH public key, IPs, storage pool.
- **Kubernetes** — app secrets live in OpenBao (`secret/<app>`) and reach the cluster through an `ExternalSecret` in the app's `templates/` (ClusterSecretStore `openbao`). Current keys: `secret/tailscale`, `secret/seafile`, `secret/grafana`, `secret/ingress-auth` (bcrypt htpasswd line for the shared admin-UI login). Never put credentials in `values.yaml`. Grafana's admin password rotation needs an extra step (see `docs/GETTING-STARTED.md`).
- **Admin UIs without their own login** (Longhorn, AdGuard, Traefik dashboard) use the `basic-auth` Traefik Middleware from `kubernetes/apps/infrastructure/ingress-auth/`: add the namespace to its `values.yaml` and annotate the Ingress with `traefik.ingress.kubernetes.io/router.middlewares: <namespace>-basic-auth@kubernetescrd`.

### Ansible Inventory

Separate host groups: `proxmox` (Proxmox host), `k3s_cp` (control plane, `ansible_user: ubuntu`), `k3s_workers` (workers, `ansible_user: ubuntu`).
