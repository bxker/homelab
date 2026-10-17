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

`mise run all` is non-destructive and safe to re-run. If a Terraform plan would destroy or
replace a VM, `infra` shows the plan and asks before applying. `mise run rebuild` destroys
everything first (after you type the cluster name).

This runs four phases in order:

1. **infra** — Terraform downloads Ubuntu 24.04 cloud image, creates 3 VMs with cloud-init networking and your SSH key
2. **k3s-install** — Ansible installs k3s on the control plane, joins workers, writes `~/.kube/homelab.yaml`.
   Your `~/.kube/config` is left alone. `mise.toml` sets `KUBECONFIG` to the new file, so mise tasks (and any
   shell with `mise activate`, inside the repo) use it; elsewhere run `export KUBECONFIG=~/.kube/homelab.yaml`.
   SSH trusts each node's host key on first connect and keeps it in `ansible/known_hosts` (not in Git).
   `mise run infra-destroy` (used by `rebuild` and `destroy`) forgets them; if you replace a VM another
   way, run `ssh-keygen -R <ip> -f ansible/known_hosts` before the next `k3s-install`.
   k3s's own Traefik and ServiceLB are disabled (ArgoCD runs Traefik; MetalLB hands out IPs).
3. **gitops** — ArgoCD installs, picks up app-of-apps, deploys all charts
4. **configure** — Ansible hardens the Proxmox host

### Migrating a cluster that still runs k3s's bundled Traefik

Clusters installed before this change still run k3s's own Traefik and ServiceLB. The next
`mise run k3s-install` removes them once, with a ~30 s API restart (workloads keep running):

1. It deletes the Helm release record of k3s's `traefik-crd` chart. Without this, k3s's
   uninstall would delete every `traefik.io` CRD and with them every IngressRoute and Middleware.
2. It restarts k3s with `disable: [traefik, servicelb]` in `/etc/rancher/k3s/config.yaml`.
3. It removes ServiceLB's `service.kubernetes.io/load-balancer-cleanup` finalizer from every
   LoadBalancer Service (otherwise they could never be deleted) and waits for the uninstall.
4. k3s's uninstall also deletes the shared `traefik` IngressClass; ArgoCD recreates it. Until it
   does, Ingresses aren't routed. If the playbook warns that it's missing, sync the `traefik` app.

Check afterwards:

```bash
kubectl -n kube-system get helmchart                        # no traefik / traefik-crd
kubectl -n kube-system get ds | grep svclb                  # nothing
kubectl get ingressclass                                    # one: traefik
kubectl get svc -A --field-selector spec.type=LoadBalancer  # IPs from MetalLB (.200, .201, ...)
```

## Step 5: Access Your Services

```bash
# Get ArgoCD password and open UI
mise run argocd-password
mise run argocd-ui
# Open https://localhost:8080

# Traefik is pinned to 192.168.1.200 (see IP Address Plan)
kubectl get svc -n traefik
# Point your router's DHCP DNS at AdGuard (192.168.1.201) so *.homelab.local
# resolves everywhere, or add entries to /etc/hosts:
#   192.168.1.200  grafana.homelab.local
#   192.168.1.200  files.homelab.local
#   192.168.1.200  longhorn.homelab.local
#   192.168.1.200  adguard.homelab.local
```

## Step 6: Bootstrap OpenBao (Secrets Manager)

After `mise run gitops`, OpenBao deploys but needs a one-time initialization:

```bash
# Initialize — prints 3 unseal keys + root token. Save all to password manager.
mise run vault-init

# Unseal (enter 2 of the 3 unseal keys when prompted)
mise run vault-unseal

# Configure Kubernetes auth + ESO policy
mise run vault-setup
# (prompts for root token)
```

Then write secrets into OpenBao:

```bash
kubectl port-forward -n openbao svc/openbao 8200:8200 &
export VAULT_ADDR=http://127.0.0.1:8200
export VAULT_TOKEN=<root-token>

# Tailscale OAuth credentials (from Step 7 below)
bao kv put secret/tailscale client_id=YOUR_ID client_secret=YOUR_SECRET

# Grafana admin login (Grafana waits for this secret before it starts)
bao kv put secret/grafana admin_user=admin admin_password="$(openssl rand -base64 24)"

# Shared login for admin UIs without their own (Longhorn, AdGuard, Traefik dashboard).
# Store only the bcrypt hash; keep the password in your password manager.
# htpasswd is in apache2-utils / httpd-tools, or: docker run --rm httpd:2.4-alpine htpasswd -nbB ...
bao kv put secret/ingress-auth htpasswd="$(htpasswd -nbB admin 'YOUR_PASSWORD')"
```

### Admin UIs behind the shared login

Until `secret/ingress-auth` exists these routes are refused (404), never served without a login.

| UI | URL |
|---|---|
| Longhorn | https://longhorn.homelab.local |
| AdGuard Home | https://adguard.homelab.local |
| Traefik dashboard | internal only: `kubectl -n traefik port-forward deploy/traefik 9000:9000`, add `127.0.0.1 traefik.homelab.local` to `/etc/hosts`, open http://traefik.homelab.local:9000/dashboard/ |

To protect another UI, add its namespace to `kubernetes/apps/infrastructure/ingress-auth/values.yaml`
and annotate its Ingress with
`traefik.ingress.kubernetes.io/router.middlewares: <namespace>-basic-auth@kubernetescrd`.

### Check that Longhorn can use every node

`mise run k3s-install` installs Longhorn's prerequisites (iSCSI and NFS clients, `iscsid`,
`iscsi_tcp`) on all three nodes, control plane included, and stops `multipathd` from claiming
Longhorn's disks. Confirm Longhorn agrees:

```bash
kubectl -n longhorn-system get pods -o wide | grep longhorn-manager   # one Running per node, no restarts
kubectl -n longhorn-system get nodes.longhorn.io                      # READY True, SCHEDULABLE True for each
```

The Longhorn UI's Node page shows the same. For a full check, run Longhorn's `longhornctl check preflight`.
If a volume was already stuck because multipathd claimed its disk, reboot that node once.

### Rotate the Grafana admin password

Grafana copies the admin password into its database the first time it starts. After
that, changing `secret/grafana` only updates the Kubernetes Secret, not the login, so
reset the database to the same value:

```bash
PW=$(openssl rand -base64 24)
bao kv put secret/grafana admin_user=admin admin_password="$PW"

# Refresh the Kubernetes Secret now instead of within the hour
kubectl -n monitoring annotate externalsecret grafana-admin force-sync="$(date +%s)" --overwrite

# Set the database password to match
printf '%s' "$PW" | kubectl -n monitoring exec -i deploy/prometheus-stack-grafana -c grafana -- \
  grafana cli admin reset-admin-password --password-from-stdin
```

Keep `admin_user=admin`: changing it doesn't rename the existing database user.

If a new Grafana pod sits in `ContainerCreating` with a `Multi-Attach` error, its volume
is still attached to the old pod on another node. Delete the old pod to let it move:
`kubectl -n monitoring delete pod <old-grafana-pod>`.

> **Note:** OpenBao must be re-unsealed after every pod restart (2 of 3 keys). Run `mise run vault-unseal` when the pod restarts.

## Step 7: Set Up Tailscale

1. Go to https://login.tailscale.com/admin/settings/oauth
2. Create OAuth client with **Devices: Write** scope
3. Write credentials to OpenBao (see Step 6 above) — External Secrets Operator creates the K8s secret automatically
4. ArgoCD deploys the operator once the secret exists
5. Expose any service to your tailnet:
   ```bash
   kubectl annotate svc grafana -n monitoring tailscale.com/expose=true
   ```

## Step 8: VM Backups (Proxmox Backup Server)

`mise run configure` sends a nightly backup of every VM (02:00, snapshot mode, keep 7 daily, 4 weekly,
3 monthly) to a Proxmox Backup Server (PBS) on **another machine**, so a dead Proxmox disk doesn't take
the backups with it. It replaces the old `vzdump` cron job that wrote to the same disk as the VMs.

**1. Set up PBS (once, outside this repo).** Install PBS on a NAS or spare box, create a datastore, a
user (for example `backup@pbs`) with the `DatastoreBackup` role on it, and note the server's
fingerprint (PBS UI → Dashboard → Show Fingerprint).

**2. Put the settings in `.env`** (see `.env.example`): `PBS_SERVER`, `PBS_DATASTORE`, `PBS_USER`,
`PBS_PASSWORD`, `PBS_FINGERPRINT`. `mise run configure` stops before changing anything if one is missing.

**3. Apply it.**

```bash
mise run infra-plan   # should show only in-place updates (agent = true), no VM replaced or destroyed
mise run infra        # asks first if anything would be destroyed or replaced
mise run k3s-install  # installs qemu-guest-agent on every node
mise run configure    # adds the pbs storage and the homelab-nightly job, removes the old cron job
```

**4. Power-cycle each VM once.** Proxmox only adds the guest-agent channel after a full stop and start
(a reboot from inside the VM isn't enough). Do it one VM at a time from the Proxmox UI, wait for the
node to be Ready (`kubectl get nodes`), then re-run `mise run k3s-install` so the agent starts.
Afterwards the VM's Summary page shows its IP addresses.

**5. Check.** Datacenter → Backup shows `homelab-nightly`. Click Run now once and watch the task log;
the backups appear in the PBS UI under your datastore.

Things to know:

- Existing `pbs` storage and `homelab-nightly` job are left as they are; change them in the UI or delete
  them and re-run `mise run configure`.
- Old backups on the `local` storage aren't touched. After the first PBS backup works, delete them in the
  UI (Storage → local → Backups) to free the disk.
- Restore one VM: PBS storage → Backups → pick the VM and snapshot → Restore. Restoring a k3s node
  brings it back with its Longhorn data; see the disaster recovery runbook once it exists (#23).
- Application-level backups (Longhorn volumes, databases, etcd) are separate (#20).

## IP Address Plan

| IP              | Purpose                  |
|-----------------|--------------------------|
| 192.168.1.254   | Router / gateway         |
| 192.168.1.155   | Proxmox host             |
| 192.168.1.100   | k3s-cp-1                 |
| 192.168.1.101   | k3s-worker-1             |
| 192.168.1.102   | k3s-worker-2             |
| .200–.209       | MetalLB `homelab-static`: pinned only, never auto-assigned |
| 192.168.1.200   | Traefik (all `*.homelab.local` Ingresses) |
| 192.168.1.201   | AdGuard Home DNS: set as the router's DHCP DNS server |
| .210–.250       | MetalLB `homelab-pool`: any other LoadBalancer |

To pin another Service, pick a free IP in .200–.209, add the annotation
`metallb.io/loadBalancerIPs: <ip>`, and list it here and in
`kubernetes/apps/infrastructure/metallb/templates/pool.yaml`. If you change Traefik's IP,
change `traefikIP` in `kubernetes/apps/infrastructure/adguard-home/values.yaml` with it.

Ports on the control plane (192.168.1.100) open to the LAN for Prometheus: 10257
(controller-manager) and 10259 (scheduler) need a Kubernetes token; 2381 (etcd
metrics) is plain HTTP and read-only. If you change the control plane's IP, change
the three `endpoints` in `kubernetes/apps/infrastructure/prometheus-stack/values.yaml`
with it.
