# 🏠 Homelab — Proxmox + k3s + GitOps (MVP)

Infrastructure-as-code managed homelab. Single mini PC today, multi-node tomorrow.

## What This Repo Deploys

```
┌─────────────────────────────────────────────────────────────┐
│                    PROXMOX VE (bare metal)                   │
│                                                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                  │
│  │ k3s-cp-1 │  │ k3s-w1   │  │ k3s-w2   │                  │
│  │  2C/4G   │  │  2C/8G   │  │  2C/8G   │                  │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘                  │
│       └─────────────┼─────────────┘                         │
│              ┌──────┴──────┐                                │
│              │  Kubernetes │                                │
│              └──────┬──────┘                                │
│                     │                                       │
│    Infrastructure   │   Workloads                           │
│    ─────────────    │   ─────────                           │
│    MetalLB          │   Prometheus + Grafana                │
│    Traefik          │   Seafile                             │
│    cert-manager     │   Tailscale                           │
│    Longhorn         │                                       │
└─────────────────────────────────────────────────────────────┘

        ▲ All managed by ArgoCD (GitOps)
        │ All apps use the wrapper Helm chart pattern
   ┌────┴────┐
   │ This    │
   │ Git Repo│
   └─────────┘
```

## Resource Budget

| VM             | CPU | RAM   | Disk   | Purpose               |
|----------------|-----|-------|--------|-----------------------|
| k3s-cp-1       | 2   | 4 GB  | 20 GB  | K8s control plane     |
| k3s-worker-1   | 2   | 8 GB  | 60 GB  | K8s worker + Longhorn |
| k3s-worker-2   | 2   | 8 GB  | 60 GB  | K8s worker + Longhorn |
| **Totals**     | **6** | **20 GB** | **140 GB** | 12 GB RAM free for PVE |

## Repository Structure

```
homelab/
├── README.md                  ← You are here
├── mise.toml                  ← Task runner & tool versions
│
├── terraform/                 ← VM provisioning on Proxmox
│   ├── main.tf
│   ├── variables.tf
│   ├── k3s-vms.tf
│   ├── terraform.tfvars.example
│   └── outputs.tf
│
├── ansible/                   ← k3s install + Proxmox host config
│   ├── inventory.yml
│   └── playbooks/
│       ├── k3s.yml
│       └── proxmox.yml
│
├── kubernetes/                ← GitOps manifests (wrapper charts)
│   ├── bootstrap/
│   │   └── argocd-install.yaml
│   └── apps/
│       ├── app-of-apps.yaml
│       ├── infrastructure/
│       │   ├── metallb/       ← Chart.yaml + values.yaml + templates/
│       │   ├── traefik/
│       │   ├── cert-manager/
│       │   ├── longhorn/
│       │   └── prometheus-stack/
│       └── workloads/
│           ├── seafile/
│           └── tailscale/
│
└── docs/
    ├── GETTING-STARTED.md     ← Start here
    ├── WRAPPER-CHARTS.md      ← How the Helm pattern works
    └── FUTURE.md              ← Backlog of deferred features
```

## Quick Start

> **Full walkthrough:** [docs/GETTING-STARTED.md](docs/GETTING-STARTED.md)

```bash
# Phase 1: Provision VMs on Proxmox
cd terraform && cp terraform.tfvars.example terraform.tfvars
# edit terraform.tfvars with your IPs, API token, and SSH public key
tofu init && tofu apply

# Phase 2: Install k3s
cd ..
mise run k3s-install
# → installs k3s on CP and workers, writes ~/.kube/config

# Phase 3: Deploy ArgoCD → it syncs everything else
kubectl create namespace argocd
kubectl apply -n argocd -f kubernetes/bootstrap/argocd-install.yaml
kubectl apply -f kubernetes/apps/app-of-apps.yaml

# Phase 4: Configure Proxmox host
cd ansible && ansible-playbook -i inventory.yml playbooks/proxmox.yml
```

Or run everything at once:

```bash
mise run all
```

## Wrapper Chart Pattern

Every app in `kubernetes/apps/` is a **wrapper Helm chart** that pulls in an upstream
chart as a dependency. This gives you a place to pin versions, override values, and add
your own templates (Ingress, Secrets, ConfigMaps) alongside the upstream chart.

See [docs/WRAPPER-CHARTS.md](docs/WRAPPER-CHARTS.md) for a full explanation.

## Design Principles

1. **Everything is code.** No clicking in UIs to configure things.
2. **GitOps for K8s.** ArgoCD watches this repo. Push a commit, cluster converges.
3. **Standard nodes.** k3s runs on Ubuntu 24.04 — SSH in, upgrade packages, inspect logs.
4. **MVP first.** Ship the essentials, defer the rest (see `docs/FUTURE.md`).
5. **Wrapper charts everywhere.** Consistent pattern for every app.
