"""Check every app's render against its ArgoCD AppProject.

usage: python3 .github/scripts/check-projects.py <render dir>   (run from the repo root; needs PyYAML)

The render dir is what render-charts.sh wrote (<app dir name>.yaml per app). For each
kubernetes/apps/*/*/application.yaml this checks, as ArgoCD would at sync time:
  - the app names a project defined in argocd-projects/appprojects.yaml (not `default`),
    and that project allows the app's source repo;
  - every namespaced resource lands in a namespace the project allows;
  - every cluster-scoped kind is allowed (CreateNamespace=true counts as a Namespace);
  - nothing is on the project's namespace-resource blacklist.
It prints each app's cluster-scoped kinds and namespaces, and exits 1 on any violation.
"""
import fnmatch
import pathlib
import sys

import yaml

RENDER = pathlib.Path(sys.argv[1])
APPS = pathlib.Path("kubernetes/apps")
PROJECTS_FILE = APPS / "infrastructure/argocd-projects/appprojects.yaml"
SERVER = "https://kubernetes.default.svc"

# Scope of built-in kinds, keyed by (API group, kind). CRD kinds are read from the renders.
CLUSTER = {("", k) for k in ("Namespace", "Node", "PersistentVolume")} | {
    ("rbac.authorization.k8s.io", "ClusterRole"), ("rbac.authorization.k8s.io", "ClusterRoleBinding"),
    ("apiextensions.k8s.io", "CustomResourceDefinition"), ("apiregistration.k8s.io", "APIService"),
    ("storage.k8s.io", "StorageClass"), ("storage.k8s.io", "CSIDriver"), ("storage.k8s.io", "VolumeAttachment"),
    ("scheduling.k8s.io", "PriorityClass"), ("node.k8s.io", "RuntimeClass"), ("networking.k8s.io", "IngressClass"),
    ("admissionregistration.k8s.io", "ValidatingWebhookConfiguration"),
    ("admissionregistration.k8s.io", "MutatingWebhookConfiguration"),
    ("admissionregistration.k8s.io", "ValidatingAdmissionPolicy"),
    ("admissionregistration.k8s.io", "ValidatingAdmissionPolicyBinding"),
}
NAMESPACED = {("", k) for k in (
    "ConfigMap", "Endpoints", "LimitRange", "PersistentVolumeClaim", "Pod", "ResourceQuota",
    "Secret", "Service", "ServiceAccount")} | {
    ("apps", k) for k in ("DaemonSet", "Deployment", "ReplicaSet", "StatefulSet")} | {
    ("batch", "Job"), ("batch", "CronJob"), ("rbac.authorization.k8s.io", "Role"),
    ("rbac.authorization.k8s.io", "RoleBinding"), ("networking.k8s.io", "Ingress"),
    ("networking.k8s.io", "NetworkPolicy"), ("policy", "PodDisruptionBudget"),
    ("discovery.k8s.io", "EndpointSlice"), ("autoscaling", "HorizontalPodAutoscaler"),
    ("coordination.k8s.io", "Lease"),
}


class Loader(yaml.SafeLoader):
    """SafeLoader that reads a bare `=` (YAML 1.1's value tag, used in some CRD enums) as a string."""


Loader.add_constructor("tag:yaml.org,2002:value", lambda loader, node: loader.construct_scalar(node))


def docs(path):
    return [d for d in yaml.load_all(path.read_text(), Loader=Loader) if isinstance(d, dict) and d.get("kind")]


def group_of(doc):
    api = doc.get("apiVersion", "")
    return api.split("/")[0] if "/" in api else ""


def matches(rules, group, kind):
    return any(fnmatch.fnmatchcase(group, r.get("group", "")) and fnmatch.fnmatchcase(kind, r.get("kind", ""))
               for r in rules or [])


projects = {p["metadata"]["name"]: p["spec"] for p in docs(PROJECTS_FILE) if p["kind"] == "AppProject"}
renders = {f.stem: docs(f) for f in RENDER.glob("*.yaml") if not f.is_symlink()}

# Scope of custom kinds: every CRD in any app's render
for app_docs in renders.values():
    for d in app_docs:
        if d["kind"] == "CustomResourceDefinition":
            key = (d["spec"]["group"], d["spec"]["names"]["kind"])
            (CLUSTER if d["spec"].get("scope") == "Cluster" else NAMESPACED).add(key)

errors = []
for app_file in sorted(APPS.glob("*/*/application.yaml")):
    app = yaml.safe_load(app_file.read_text())
    app_dir = app_file.parent
    name, spec = app["metadata"]["name"], app["spec"]
    project_name, dest_ns = spec.get("project"), spec["destination"].get("namespace", "")
    where = f"{name} ({app_dir})"
    project = projects.get(project_name)
    if project is None:
        errors.append(f"{where}: project {project_name!r} isn't defined in {PROJECTS_FILE}")
        continue
    if not any(fnmatch.fnmatchcase(spec["source"]["repoURL"], r) for r in project.get("sourceRepos", [])):
        errors.append(f"{where}: source {spec['source']['repoURL']} not in project {project_name}'s sourceRepos")
    if app_dir.name not in renders:
        if (app_dir / "Chart.yaml").exists() or (app_dir / "kustomization.yaml").exists():
            errors.append(f"{where}: no render in {RENDER} (render-charts.sh should have written {app_dir.name}.yaml)")
        continue

    def dest_ok(ns):
        return any(fnmatch.fnmatchcase(SERVER, d.get("server", SERVER)) and fnmatch.fnmatchcase(ns, d.get("namespace", ""))
                   for d in project.get("destinations", []))

    cluster_kinds, namespaces = set(), set()
    wanted = list(renders[app_dir.name])
    if "CreateNamespace=true" in (spec.get("syncPolicy") or {}).get("syncOptions", []):
        wanted.append({"apiVersion": "v1", "kind": "Namespace", "metadata": {"name": dest_ns}})
    for d in wanted:
        group, kind = group_of(d), d["kind"]
        label = f"{group + '/' if group else ''}{kind}"
        if (group, kind) in CLUSTER:
            cluster_kinds.add(label)
            if not matches(project.get("clusterResourceWhitelist"), group, kind) or \
                    matches(project.get("clusterResourceBlacklist"), group, kind):
                errors.append(f"{where}: cluster-scoped {label} {d['metadata'].get('name')} not permitted in project {project_name}")
        elif (group, kind) in NAMESPACED:
            ns = d["metadata"].get("namespace") or dest_ns
            namespaces.add(ns)
            if not dest_ok(ns):
                errors.append(f"{where}: {label} {d['metadata'].get('name')} in namespace {ns!r}, not a destination of project {project_name}")
            if matches(project.get("namespaceResourceBlacklist"), group, kind) or (
                    project.get("namespaceResourceWhitelist") and not matches(project["namespaceResourceWhitelist"], group, kind)):
                errors.append(f"{where}: {label} {d['metadata'].get('name')} is blocked in project {project_name}")
        else:
            errors.append(f"{where}: don't know whether {label} is cluster-scoped; add it to check-projects.py")
    print(f"{name:18} project={project_name:15} namespaces={sorted(namespaces)} cluster-scoped={sorted(cluster_kinds) or '-'}")

for e in errors:
    print(f"::error::{e}")
print("RESULT:", "FAIL" if errors else "PASS")
sys.exit(1 if errors else 0)
