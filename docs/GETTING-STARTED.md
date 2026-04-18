# Getting Started — From Windows to Running Cluster

This guide covers everything from a brand new mini PC running Windows to a fully
automated Kubernetes homelab.

## Big Picture

```
  MANUAL (you, ~30 min)             AUTOMATED (this repo)
  ─────────────────────             ─────────────────────

  1. Download Proxmox ISO           4. mise run infra
  2. Flash USB drive                    → creates Ubuntu VMs
  3. Boot mini PC, install PVE       5. mise run k3s-install
     → pick IP, set password            → bootstraps k3s cluster
     → reboot                        6. mise run gitops
                                        → ArgoCD deploys everything
  Done. Never touch the              7. mise run configure
  mini PC physically again.             → hardens Proxmox host
```

## Step 1: Install Proxmox VE

### What you need

- Your mini PC (Windows will be erased)
- A USB flash drive (4 GB+)
- A monitor and keyboard (only for install)
- Ethernet cable to your router

### Flash the ISO

1. Download Proxmox VE ISO from https://www.proxmox.com/en/downloads
2. Flash to USB with [balenaEtcher](https://etcher.balena.io) or [Rufus](https://rufus.ie)

### Boot and install

1. Plug USB into mini PC, power on
2. Enter boot menu (common keys: `F12`, `F11`, `F7`, `Del`)
3. Select "Install Proxmox VE (Graphical)"
4. Pick your SSD as the target disk (this erases Windows)
5. Choose filesystem: **ext4** (simple) or **ZFS** (better integrity, uses more RAM)
6. Set timezone
7. Set root password — remember this

8. **Network configuration** (the important part):
   ```
   Hostname:    pve.homelab.local
   IP Address:  192.168.1.155/24     ← pick a static IP outside DHCP range
   Gateway:     192.168.1.254        ← your router
   DNS:         192.168.1.254
   ```

9. Install, remove USB when prompted, reboot

### First login

Open `https://192.168.1.155:8006` from another computer. Login as `root`.
Disconnect the monitor and keyboard — you won't need them again.

## Step 2: Create API Token for Terraform

1. Proxmox UI → **Datacenter → Permissions → API Tokens → Add**
2. User: `root@pam`, Token ID: `homelab`
3. **Uncheck** "Privilege Separation"
4. Copy the token: `root@pam!homelab=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`

## Step 3: Install Tools

```bash
# mise handles all tool versions
mise install          # installs tofu, kubectl, helm, ansible

# Verify
mise run status       # should fail gracefully — cluster doesn't exist yet
```

## Step 4: Configure and Deploy

```bash
# Fill in your values
cd terraform
cp terraform.tfvars.example terraform.tfvars
# Edit: set your Proxmox IP, API token, SSH public key, network info

# Update Ansible inventory
# Edit ansible/inventory.yml → set pve ansible_host to your Proxmox IP

# Deploy everything
mise run all
```

This runs four phases in order:

1. **infra** — Terraform downloads Ubuntu 24.04 cloud image, creates 3 VMs with cloud-init networking and your SSH key
2. **k3s-install** — Ansible installs k3s on the control plane, joins workers, writes `~/.kube/config`
3. **gitops** — ArgoCD installs, picks up app-of-apps, deploys all charts
4. **configure** — Ansible hardens the Proxmox host

## Step 5: Access Your Services

```bash
# Get ArgoCD password and open UI
mise run argocd-password
mise run argocd-ui
# Open https://localhost:8080

# Check what MetalLB assigned to Traefik
kubectl get svc -n traefik
# EXTERNAL-IP is your ingress IP — add to /etc/hosts:
#   192.168.1.201  grafana.homelab.local
#   192.168.1.201  files.homelab.local
#   192.168.1.201  longhorn.homelab.local
```

## Step 6: Set Up Tailscale

Before Tailscale deploys, create the OAuth secret:

1. Go to https://login.tailscale.com/admin/settings/oauth
2. Create OAuth client with **Devices: Write** scope
3. Create the K8s secret:
   ```bash
   kubectl create namespace tailscale
   kubectl create secret generic operator-oauth \
     --namespace tailscale \
     --from-literal=client_id=YOUR_ID \
     --from-literal=client_secret=YOUR_SECRET
   ```
4. ArgoCD will deploy the operator automatically
5. Expose any service to your tailnet:
   ```bash
   kubectl annotate svc grafana -n monitoring tailscale.com/expose=true
   ```

## IP Address Plan

| IP              | Purpose                  |
|-----------------|--------------------------|
| 192.168.1.254   | Router / gateway         |
| 192.168.1.155   | Proxmox host             |
| 192.168.1.100   | k3s-cp-1                 |
| 192.168.1.101   | k3s-worker-1             |
| 192.168.1.102   | k3s-worker-2             |
| .200–.250       | MetalLB pool (K8s LBs)   |
