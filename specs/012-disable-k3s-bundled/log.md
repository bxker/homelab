## analyst · spec · done
2026-10-13T04:24:36Z

**Did:** Wrote spec.md after reproducing the change in a lab k3s v1.36.5: naive disable deletes all traefik.io CRDs and their CRs; protected sequence keeps them. 6 criteria, 2 open questions.

**Evidence:**
- k3s docs: `--disable` actively uninstalls; `manifests/traefik.yaml` holds HelmCharts traefik-crd + traefik
- traefik-crd chart 40.1.5: IngressRoute/Middleware CRDs are templates without `resource-policy: keep`
- lab results in `specs/012-disable-k3s-bundled/lab/README.md`

**Changed files:** `specs/012-disable-k3s-bundled/{spec.md,lab/*}`

**Open issues:** OQ1 automate vs runbook; OQ2 IngressClass gap

**Next:** Spec gate

## architect · plan · done
2026-10-13T04:30:03Z

**Did:** Wrote plan.md: task-file design (testable against the lab via a systemctl shim), 2 tasks.

**Changed files:** `specs/012-disable-k3s-bundled/plan.md`

**Next:** Plan gate

## implementer · T1 · done
2026-10-13T04:34:16Z

**Did:** `tasks/k3s-disable-bundled.yml` (detect bundled charts → drop traefik-crd release record → write config → restart → readyz → strip ServiceLB finalizer → wait for charts gone → bounded IngressClass wait + warning), included in the server play with `k3s_bin`, finalizer and retry vars.

**Evidence:**
- lab runs 1–3 (see `lab/README.md`): migration keeps CRDs/CRs, removes bundled charts and svclb; re-run changed=0; fresh node writes config only
- `ansible-playbook --syntax-check` ok; `ansible-lint` production profile (first attempt hit no-handler ×4 → explicit `k3s_needs_restart` fact)

**Changed files:** `ansible/playbooks/tasks/k3s-disable-bundled.yml`, `ansible/playbooks/k3s.yml`

**Next:** review T1

## infra-reviewer · T1 · done
2026-10-13T04:34:16Z

**Findings:**
- MEDIUM (owner action, documented): the migration deletes the shared `traefik` IngressClass; Ingresses aren't routed until ArgoCD recreates it. The playbook waits up to 5 min and warns.
- LOW: the finalizer patch replaces the list without the ServiceLB entry. Other finalizers on the same Service are kept (merge patch with the filtered list).
- LOW: if the restart happens but the uninstall wait fails (>5 min), a re-run restarts again (bundled charts still present) and resumes safely; the release-record deletion is idempotent.

**Next:** commit T1, T2
