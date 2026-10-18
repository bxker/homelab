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
3. **gitops** — ArgoCD installs, picks up app-of-apps, deploys all charts in sync waves. Each wave waits
   until the previous one is Healthy. On a fresh cluster ArgoCD stops at OpenBao (wave 4) until you
   initialize and unseal it in Step 6 (`mise run vault-init`, then `mise run vault-unseal`).
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
# resolves everywhere, and add a SECONDARY DNS outside the cluster (the router
# itself or 1.1.1.1) so the LAN still resolves while the cluster is down.
# (*.homelab.local only resolves through AdGuard.) Or add entries to /etc/hosts:
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

On a fresh cluster ArgoCD waits at wave 4. OpenBao is expected to report Progressing until it is
initialized and unsealed. After `mise run vault-unseal`, External Secrets (wave 5) syncs on its own.
You don't need a manual sync. In the lab, app-of-apps kept its sync running and resumed once the
wave it waited on turned Healthy.

Waves 6 to 10 finish only after `mise run vault-setup` and the `bao kv put` commands below.
Until `secret/grafana` exists, Grafana keeps prometheus-stack (wave 6) Progressing. That is expected
to hold Seafile (wave 10) for up to about 10 minutes, until Grafana's Deployment turns Degraded.

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

# Signal alerts: secret/signal comes later, in step 4 of "Signal alerts" below
# (after linking Signal and checking what is firing).
# Watchdog ping (healthchecks.io check: see step 5 there)
bao kv put secret/healthchecks url=YOUR_PING_URL
```

### Signal alerts

Alertmanager sends alerts to Signal through the `alerting` app. Watchdog goes only to a
healthchecks.io check, which tells you when alerting itself is down. Until the secrets exist:

- `alerting` and prometheus-stack show Degraded (ExternalSecret not ready). This holds Seafile (wave 10) for only about 10 s.
- The adapter pod waits in `CreateContainerConfigError`, so no alert reaches Signal.
- Alertmanager still runs. Only its Watchdog ping fails until `secret/healthchecks` exists.

Set it up once `alerting` is deployed, with `VAULT_ADDR` and `VAULT_TOKEN` set as above.

Run each port-forward below in the foreground, in its own terminal, and stop it (Ctrl-C) right
after the step that needs it. While it runs, anything on your machine can use signal-cli's or
Alertmanager's API without a login, including a web page open in your browser.

1. Link signal-cli to your Signal account as a secondary device:

   ```bash
   # own terminal; Ctrl-C after step 2
   kubectl -n alerting port-forward svc/signal-cli 8080:8080
   ```

   Open `http://localhost:8080/v1/qrcodelink?device_name=homelab` in a browser.
   In the Signal app, open Settings → Linked devices → Link new device, and scan the QR code.

2. Create a Signal group for alerts in the Signal app. Then list the groups the linked account sees:

   ```bash
   curl -s http://localhost:8080/v1/groups/+YOUR_NUMBER
   ```

   Copy the alert group's `id` field (it starts with `group.`). To get alerts in a chat with
   one person instead, use their `+number` as the recipient. Stop the signal-cli port-forward.

3. Check what is already firing. The first send after step 4 delivers every firing alert at once.

   ```bash
   # own terminal; Ctrl-C when done here (start it again for step 6 if you use a local amtool)
   kubectl -n monitoring port-forward svc/prometheus-stack-kube-prom-alertmanager 9093:9093
   ```

   Open `http://localhost:9093/#/alerts`. Fix or silence the noisy alerts before the next step.
   Then stop the port-forward.

4. Store the sending number and the recipient:

   ```bash
   bao kv put secret/signal number=+YOUR_NUMBER recipient=YOUR_GROUP_ID_OR_NUMBER
   kubectl -n alerting annotate externalsecret signal force-sync="$(date +%s)" --overwrite
   ```

   The adapter pod starts by itself once the Secret exists.

5. Create a check on healthchecks.io with period 5 minutes and grace 10 minutes. Store its ping URL:

   ```bash
   bao kv put secret/healthchecks url=YOUR_PING_URL
   kubectl -n monitoring annotate externalsecret alertmanager-healthchecks force-sync="$(date +%s)" --overwrite
   ```

   Alertmanager pings about every 2 minutes. Within a few minutes the check should show a recent ping.
   If it doesn't, delete the Alertmanager pod once so it remounts the Secret (expected not to be needed).

6. Send a test alert. `mise install` doesn't install `amtool`. Use the one in the Alertmanager
   release archive with the port-forward from step 3 (stop it afterwards), or run it inside the
   pod (second command).

   ```bash
   amtool --alertmanager.url=http://localhost:9093 alert add alertname=SignalTest namespace=alerting \
     severity=warning --annotation=summary="Test alert from amtool"

   # Or, without a local amtool:
   kubectl -n monitoring exec alertmanager-prometheus-stack-kube-prom-alertmanager-0 -c alertmanager -- \
     amtool --alertmanager.url=http://localhost:9093 alert add alertname=SignalTest namespace=alerting \
     severity=warning --annotation=summary="Test alert from amtool"
   ```

   A Signal message should arrive within about 30 s. To resolve the alert, run the same
   `alert add` again with `--end="$(date -u +%Y-%m-%dT%H:%M:%SZ)"` added. If you skip that, it
   resolves on its own after 5 minutes. The resolved message follows within about 5 minutes.

   To check that the link survives a restart, run
   `kubectl -n alerting delete pod -l app=signal-cli`, wait for the new pod to be Ready, and
   send the test alert again. It should arrive without relinking.

7. signal-cli keeps the linked account on a 1Gi Longhorn volume. If that PVC is lost, link
   again with step 1, and remove the old `homelab` entry under Linked devices in the Signal app.

Routing lives only in `kubernetes/apps/infrastructure/prometheus-stack/values.yaml`.
Alertmanager ignores AlertmanagerConfig resources. The adapter, signal-cli and Alertmanager's
API have no login. NetworkPolicies let only Alertmanager reach the adapter, only the adapter
reach signal-cli, and only Prometheus and Grafana reach Alertmanager. The adapter itself may
only reach DNS and signal-cli. `kubectl port-forward` still works. The policies stop other pods,
not the nodes: kube-router lets traffic from a pod's own node through, so processes on the
nodes and hostNetwork pods can still reach these APIs.

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
> A sealed OpenBao doesn't block later commits to apps that already synced, or new apps in a sync
> that doesn't include OpenBao. It holds waves 5 and later only when the same app-of-apps sync also
> applies OpenBao.

### If app-of-apps looks stuck

See what app-of-apps waits on:

```bash
kubectl -n argocd get app app-of-apps -o jsonpath='{.status.operationState.message}'
```

The message reads `waiting for healthy state of …` and names the app. Fix that app, and the
sync carries on.

To end the operation instead, use the argocd CLI (not installed by `mise install`). With `--core`
it talks to the cluster through your kubeconfig, so it needs no login. It uses the kube context's
namespace, so point that at `argocd` first:

```bash
kubectl config set-context --current --namespace=argocd
argocd --core app terminate-op app-of-apps
```

Auto-sync is expected to skip the commit whose sync you ended. Start a sync by hand with
`argocd --core app sync app-of-apps`, or push a new commit. `mise run sync` doesn't start a sync.
It only re-applies the app-of-apps manifest.

When you're done, set the namespace back to what it was (`default` in the kubeconfig `k3s-install` writes):
`kubectl config set-context --current --namespace=default`.

To remove only the health gate, delete the `resource.customizations.health.argoproj.io_Application`
key from `kubernetes/apps/infrastructure/argocd/argocd-cm.yaml` and commit. The `argocd` app's own
sync then drops the key from `argocd-cm`. Children keep their `syncPolicy.retry` and CI keeps its
check. If you ran `mise run gitops` after the health check merged, its server-side apply also owns
the key, so run `mise run gitops` again after the commit.

### Pod Security

Every namespace an app creates carries Pod Security `warn` and `audit` labels at `restricted`.
`seafile` and `alerting` also enforce `baseline`. The other namespaces enforce nothing yet. That
comes later, once the warnings show what each app needs (#33). Check the labels:

```bash
kubectl get ns -L pod-security.kubernetes.io/enforce,pod-security.kubernetes.io/warn
```

The labels arrive with each app's next sync. If a namespace still shows none after its app synced,
sync that app by hand (see "If app-of-apps looks stuck" for `argocd --core app sync`).

`warn` shows up as a warning when ArgoCD applies a workload that breaks `restricted`. k3s has no API
audit log by default, so `audit` records nothing there. To see which running pods a stricter level
would reject, try it without changing anything:

```bash
kubectl label --dry-run=server --overwrite ns <namespace> pod-security.kubernetes.io/enforce=baseline
```

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
| 192.168.1.201   | AdGuard Home DNS (2 replicas): set as the router's DHCP DNS server, with a secondary outside the cluster |
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
