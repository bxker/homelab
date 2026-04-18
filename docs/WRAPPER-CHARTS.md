# Wrapper Charts — How the Helm Pattern Works

Every app in this repo uses the same pattern: a **wrapper Helm chart** that pulls in
an upstream chart as a subchart dependency, then layers on your customizations.

## Why not just inline values in ArgoCD?

You could define a Helm source with `valuesObject` directly in ArgoCD's Application YAML.
That works, but wrapper charts give you:

1. **Extra templates** — add your own Ingress, ConfigMap, Secret, or CRD alongside the
   upstream chart's resources without ArgoCD-specific hacks.
2. **Testability** — run `helm template` locally to preview what will be rendered. No
   cluster needed.
3. **Portability** — your chart works with or without ArgoCD. Deploy with plain `helm
   install` if needed.
4. **Version pinning** — `Chart.yaml` locks the upstream version. Upgrade by bumping the
   version string and pushing to Git.
5. **Consistency** — every app follows the same structure. No guessing where config lives.

## Structure

```
kubernetes/apps/infrastructure/metallb/
├── Chart.yaml          ← declares upstream metallb as a dependency
├── values.yaml         ← overrides for the upstream chart (prefixed by subchart name)
├── application.yaml    ← ArgoCD Application pointing to this directory
└── templates/
    └── pool.yaml       ← YOUR extra resources (IPAddressPool, L2Advertisement)
```

## How It Works

### Chart.yaml — declare the dependency

```yaml
apiVersion: v2
name: metallb
version: 1.0.0
dependencies:
  - name: metallb                              # upstream chart name
    version: "0.14.*"                           # pin major.minor, float patch
    repository: https://metallb.github.io/metallb  # upstream Helm repo
```

The `name` in dependencies must match the upstream chart's actual name. The `version`
field supports semver ranges — `"0.14.*"` means "any 0.14.x release."

### values.yaml — configure the upstream chart

Values for the subchart are nested under the subchart's name:

```yaml
# This key MUST match the dependency name (or alias) in Chart.yaml
metallb:
  speaker:
    frr:
      enabled: false
```

If you set an `alias` in Chart.yaml, use the alias as the key instead:

```yaml
# Chart.yaml has: alias: seafile
seafile:
  initMode: true
```

### templates/ — your extra resources

Anything in `templates/` is rendered alongside the subchart's resources. This is
where you add things the upstream chart doesn't provide:

- Custom Ingress routes
- IPAddressPool / L2Advertisement for MetalLB
- ClusterIssuers for cert-manager
- Secrets, ConfigMaps, CronJobs, whatever you need

These templates have full access to Helm's template functions, `.Values`, `.Release`, etc.

### application.yaml — tell ArgoCD about this chart

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: metallb
  namespace: argocd
spec:
  source:
    repoURL: https://github.com/bxker/homelab.git
    targetRevision: main
    path: kubernetes/apps/infrastructure/metallb   # points to the wrapper chart dir
  destination:
    server: https://kubernetes.default.svc
    namespace: metallb-system
  syncPolicy:
    automated: { prune: true, selfHeal: true }
    syncOptions: [CreateNamespace=true]
```

ArgoCD sees the `Chart.yaml`, runs `helm dependency build`, then `helm template`, and
applies the result. You never run Helm commands yourself — ArgoCD handles it.

## Adding a New App

1. **Create the directory:**
   ```
   kubernetes/apps/workloads/my-app/
   ├── Chart.yaml
   ├── values.yaml
   ├── application.yaml
   └── templates/       (optional — for extra resources)
   ```

2. **Find the upstream chart:**
   ```bash
   helm search hub my-app
   # or check ArtifactHub: https://artifacthub.io
   ```

3. **Write Chart.yaml:**
   ```yaml
   apiVersion: v2
   name: my-app
   version: 1.0.0
   dependencies:
     - name: my-app
       version: "X.Y.*"
       repository: https://charts.example.com
   ```

4. **Write values.yaml** — check upstream defaults:
   ```bash
   helm show values my-app/my-app
   ```

5. **Write application.yaml** — copy from an existing one, change name/path/namespace.

6. **Test locally:**
   ```bash
   cd kubernetes/apps/workloads/my-app
   helm dependency build
   helm template my-app . --namespace my-app
   ```

7. **Deploy:** commit, push. ArgoCD syncs automatically.

## Upgrading an Upstream Chart

1. Edit `Chart.yaml` — bump the version:
   ```yaml
   dependencies:
     - name: metallb
       version: "0.15.*"    # was 0.14.*
   ```

2. Commit and push. ArgoCD detects the change, rebuilds deps, and deploys the new version.

3. Check ArgoCD UI for sync status and any drift.

## Tips

- **Always prefix subchart values** with the dependency name. Bare keys go to YOUR
  templates, not the subchart.
- **Use `alias`** when the upstream chart name conflicts with your wrapper name, or when
  you have multiple instances of the same chart.
- **Don't commit `charts/` directory** — it contains downloaded tarballs. ArgoCD rebuilds
  them. Add `charts/` to `.gitignore`.
- **`helm dependency build`** downloads tarballs into `charts/`. Run it locally to test.
  ArgoCD runs it automatically.
