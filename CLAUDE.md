# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Stack

Proxmox VE (bare metal) → 3 Ubuntu 24.04 VMs via Terraform (cloud-init) → k3s via Ansible → ArgoCD GitOps.

IPs configured in `mise.toml` env vars and `terraform.tfvars` (both gitignored or loaded from `.env`).

## Common Commands

All tasks run through `mise`:

```bash
mise run all            # full deploy: infra → k3s-install → gitops → configure
mise run infra          # terraform apply (provision VMs)
mise run k3s-install    # ansible: install k3s, write ~/.kube/config
mise run gitops         # install ArgoCD + apply app-of-apps
mise run configure      # ansible: harden Proxmox host
mise run status         # kubectl get nodes + ArgoCD apps + LB services
mise run deps           # helm dependency build for all wrapper charts
mise run destroy        # terraform destroy
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

2. **Ansible** (`ansible/playbooks/k3s.yml`) — installs k3s on control plane (`--cluster-init`), joins workers via node token, patches kubeconfig server address from `127.0.0.1` to the CP IP, writes to `~/.kube/config`.

3. **ArgoCD** bootstrapped manually once (`kubernetes/bootstrap/argocd-install.yaml` — just a ConfigMap setting `server.insecure: "true"`; the full install YAML is applied separately). After bootstrap, ArgoCD self-manages everything.

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

Infrastructure apps use `argocd.argoproj.io/sync-wave` annotations in `application.yaml` to control ordering (e.g., MetalLB before Traefik).

### Adding a New App

1. Create `kubernetes/apps/workloads/<app>/` with `Chart.yaml`, `values.yaml`, `application.yaml`
2. Copy `application.yaml` from an existing app; update `name`, `path`, `namespace`
3. Test locally: `helm dependency build && helm template <app> .`
4. Commit and push — ArgoCD picks it up automatically

Update `repoURL` in `app-of-apps.yaml` and all `application.yaml` files to your actual Git remote before first deploy.

### Terraform Notes

`terraform.tfvars` (gitignored) requires `ssh_public_key` — your workstation's public key for SSH access to Ubuntu VMs. Use `local-zfs` for `storage_pool` if Proxmox was installed with ZFS.

### Secrets

Secrets are kept out of Git via two mechanisms:
- **`.env`** (gitignored) — Proxmox URL, API token, node name. Loaded by mise via `_.file = ".env"`. See `.env.example` for the template.
- **`terraform.tfvars`** (gitignored) — SSH public key, IPs, storage pool.
- **Kubernetes values.yaml** — passwords marked `"changeme"` are placeholders. Replace with Sealed Secrets or SOPS before production use.

### Ansible Inventory

Separate host groups: `proxmox` (Proxmox host), `k3s_cp` (control plane, `ansible_user: ubuntu`), `k3s_workers` (workers, `ansible_user: ubuntu`).
