## analyst · spec · done
2026-10-13T03:57:14Z

**Did:** Wrote spec.md: 6 criteria, 2 open questions. The CLAUDE.md Secrets item was already done in #44; added the stale pool.yaml comment (from #46) and the missing ingress-auth in the README.

**Evidence:**
- `git ls-files` → 3 `.DS_Store`; README diagram/tree vs `kubernetes/apps/`; `argocd-ingress.yaml` applied only in README

**Changed files:** `specs/018-repo-hygiene/spec.md`

**Open issues:** OQ1 move Tailscale, OQ2 argocd-ingress in mise gitops

**Next:** Spec gate
