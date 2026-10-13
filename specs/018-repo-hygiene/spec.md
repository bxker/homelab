# Spec: Repo hygiene: macOS cruft, stale docs, Tailscale location

Ticket: gh:18 · Size: standard (moves a GitOps app path) · Status: approved

## Problem
Three `.DS_Store` files are committed. Several docs no longer match the repo: the Tailscale values tell
you to create its OAuth Secret by hand (OpenBao + ESO does it now), the README diagram and tree put
Prometheus and Tailscale under the wrong group and miss `ingress-auth`, the README Quick Start bypasses
the `mise` tasks, and the MetalLB pool comment still lists `.203` as a pin (#46 freed it). Tailscale, an
infrastructure component, lives under `workloads/`. The `CLAUDE.md` Secrets item was already fixed in #44.

## Goals
- No OS cruft in Git, and none can be re-added by accident.
- Docs and comments describe the repo as it is today.

## Non-goals
- ArgoCD self-management (#25). Changing any deployed resource's content.

## Acceptance criteria
- **AC1**: Given the repo, then `git ls-files` lists no `.DS_Store`, and `.gitignore` ignores `.DS_Store`.
- **AC2**: Given `tailscale/values.yaml`, then its comments describe OpenBao `secret/tailscale` → ESO →
  `operator-oauth`, with no `kubectl create secret` instruction.
- **AC3** (OQ1): Given the move, then Tailscale lives at `kubernetes/apps/infrastructure/tailscale/` with its
  `application.yaml` path updated, the Application keeps its name, and its rendered manifests are
  byte-identical before and after.
- **AC4**: Given `README.md`, then the diagram and tree match `kubernetes/apps/` (including `ingress-auth`),
  and Quick Start uses `mise` tasks only.
- **AC5**: Given `metallb/templates/pool.yaml`, then its pin comment lists only `.200` and `.201`.
- **AC6** (OQ2): Given a fresh `mise run gitops`, then `argocd-ingress.yaml` is applied without a manual step.

## Constraints
- ArgoCD identifies an Application by name, so moving the directory and changing `spec.source.path`
  updates the same Application in place. Nothing is pruned or recreated if the rendered output is unchanged.

## Requirement changes
None.

## Open questions
None. Resolved at the Spec gate: (1) move Tailscale to `infrastructure/`; (2) `mise run gitops` applies `argocd-ingress.yaml`.
