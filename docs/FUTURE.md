# Future — Deferred Features and Expansion Ideas

Everything below was considered for the MVP but deferred to keep the initial setup
focused. Each section includes enough context to pick it up when you're ready.

## Workloads

### Home Assistant (VM on Proxmox)
- Dedicated HAOS VM managed by Ansible (not K8s — needs USB passthrough for Zigbee)
- Add `terraform/homeassistant.tf` for the VM definition
- Add `ansible/playbooks/homeassistant.yml` for API-based config
- Download HAOS qcow2: https://www.home-assistant.io/installation/alternative
- USB passthrough for Zigbee dongle (find device ID with `lsusb` on PVE host)

### Vaultwarden (Password Manager)
- Lightweight Bitwarden-compatible server
- Wrapper chart with raw manifests in `templates/` (no upstream Helm chart needed)
- Tiny PVC (1 GB), very low resource usage
- Expose via Traefik Ingress with TLS

### Pi-hole / AdGuard Home (DNS)
- Network-wide ad blocking
- Can run in K8s with MetalLB giving it a static LAN IP for DNS
- Or run in a dedicated LXC container (simpler for DNS bootstrapping)
- Once running, point your router's DHCP DNS to it
- Add local DNS records for `*.homelab.local` → Traefik LB IP

### Nextcloud / Media Server
- If Seafile doesn't cover your needs, Nextcloud has calendars, contacts, etc.
- Heavy on resources (~1 GB RAM minimum)
- Consider Jellyfin/Plex for media streaming (separate from file sync)

### Uptime Kuma (Status Page)
- Simple service monitoring with a nice UI
- Raw manifest wrapper chart (Deployment + PVC + Ingress)
- Check if all your services are healthy at a glance

### Authelia / Authentik (SSO)
- Single sign-on gateway for all self-hosted apps
- Sits between Traefik and your services via ForwardAuth middleware
- Provides 2FA (TOTP, WebAuthn) across everything
- More complex to configure — do this after core services are stable

## Infrastructure

### Services LXC Container
- Lightweight Debian container on Proxmox for non-K8s services
- NFS server for bulk file storage
- Docker host for anything that doesn't fit in K8s
- Add `terraform/services-lxc.tf` and Ansible playbook

### Secrets Management
- **Sealed Secrets** — encrypt secrets in Git, controller decrypts in cluster
- **SOPS + age** — encrypt YAML values, decrypt at sync time
- **External Secrets Operator** — pull from Vault, AWS SSM, etc.
- For homelab, SOPS + age is the sweet spot (no extra controller needed)

### Automated Backups
- **Velero** — K8s-native backup/restore for PVCs and resources
- **Proxmox Backup Server** — dedicated backup target for VM snapshots
- **Longhorn backup target** — configure NFS or S3 endpoint for volume backups
- The Ansible playbook already sets up basic vzdump cron, but a proper backup
  strategy needs a dedicated target

### Alertmanager
- Part of the prometheus-stack but disabled in MVP
- Configure with Slack, Discord, or email notifications
- Set up alerts for: node down, disk full, pod crash loops, certificate expiry

## Scaling

### Adding Physical Nodes
- Install Proxmox on new hardware
- Join to Proxmox cluster: `pvecm create` / `pvecm add`
- Extend Terraform to target the new node
- Add new k3s worker IPs to `terraform.tfvars` and `ansible/inventory.yml`
- Longhorn auto-rebalances storage replicas

### Ceph (Replacing Longhorn)
- Consider when you have 3+ physical nodes with dedicated OSD disks
- Much heavier than Longhorn (~2 GB RAM per OSD)
- Provides block, object (S3), and filesystem storage
- Proxmox has built-in Ceph management
- k3s works with Ceph via the rbd CSI driver

### High Availability Control Plane
- Add 2 more control plane nodes (3 total) for etcd quorum
- Put a virtual IP (kube-vip) in front of the API servers
- Update k3s server config with `--tls-san` pointing to the VIP

### GitOps Improvements
- **Renovate Bot** — auto-creates PRs when upstream chart versions update
- **ArgoCD Image Updater** — auto-bumps container image tags
- **Pre-commit hooks** — lint Helm charts and YAML before pushing

## Network

### Real Domain + Let's Encrypt
- Buy a domain, use Cloudflare for DNS
- cert-manager DNS-01 challenge for real TLS certs
- Cloudflare Tunnel for external access without port forwarding
- Split-horizon DNS: internal → LAN IPs, external → tunnel

### VLAN Segmentation
- Separate IoT devices from trusted network
- Requires a managed switch and router VLAN support
- Proxmox can bridge VMs to specific VLANs

### 10GbE / 2.5GbE Between Nodes
- Helps with Longhorn/Ceph replication throughput
- Most modern mini PCs have 2.5GbE built in
- Direct cable between nodes or a 2.5GbE switch
