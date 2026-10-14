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
│    MetalLB          │   Seafile                             │
│    Traefik          │                                       │
│    cert-manager     │                                       │
│    Longhorn         │                                       │
│    AdGuard Home     │                                       │
│    OpenBao          │                                       │
│    Ext. Secrets     │                                       │
│    Prometheus +     │                                       │
│      Grafana        │                                       │
│    Tailscale        │                                       │
│    Ingress auth     │                                       │
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
│   └── apps/
│       ├── app-of-apps.yaml
│       ├── infrastructure/
│       │   ├── argocd/        ← kustomization.yaml: ArgoCD manages itself
│       │   ├── metallb/       ← Chart.yaml + values.yaml + templates/
│       │   ├── traefik/
│       │   ├── cert-manager/
│       │   ├── longhorn/
│       │   ├── prometheus-stack/
│       │   ├── adguard-home/
│       │   ├── openbao/
│       │   ├── external-secrets/
│       │   ├── tailscale/
│       │   └── ingress-auth/  ← shared login for admin UIs
│       └── workloads/
│           └── seafile/
│
├── .github/
│   └── workflows/
│       └── renovate-approve.yml
│
└── docs/
    ├── GETTING-STARTED.md     ← Start here
    ├── WRAPPER-CHARTS.md      ← How the Helm pattern works
    └── FUTURE.md              ← Backlog of deferred features
```

## Quick Start

> **Full walkthrough:** [docs/GETTING-STARTED.md](docs/GETTING-STARTED.md)

```bash
# One-time setup: copy and fill in the gitignored config
cp .env.example .env                                            # Proxmox URL, API token, node
cp terraform/terraform.tfvars.example terraform/terraform.tfvars  # IPs, SSH key, storage

mise run infra          # Phase 1: provision VMs on Proxmox (asks before destroying anything)
mise run k3s-install    # Phase 2: install k3s, write ~/.kube/homelab.yaml (mise sets KUBECONFIG)
mise run gitops         # Phase 3: install ArgoCD, app-of-apps and the ArgoCD Ingress
mise run configure      # Phase 4: configure the Proxmox host
```

Then bootstrap OpenBao and store app secrets ([GETTING-STARTED.md](docs/GETTING-STARTED.md) Step 6).

Or run everything at once:

```bash
mise run all
```

`mise run all` is safe to re-run: it never destroys VMs, and `infra` stops to ask if a plan
would destroy or replace one. To wipe everything and start over (all VM and Longhorn data is
lost), run `mise run rebuild` and type the cluster name when asked.

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
