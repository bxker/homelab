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
