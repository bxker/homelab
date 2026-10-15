#!/bin/sh
# usage: .github/scripts/render-charts.sh <out dir>   (run from the repo root; needs helm, kustomize)
# Renders every app the way ArgoCD does. Wrapper charts are built, linted and templated
# with the release name and namespace from the app's application.yaml; Kustomize apps
# (a kustomization.yaml, e.g. argocd) are built with kustomize. Output: <out dir>/<app dir name>.yaml
set -eu
out=$1
mkdir -p "$out"
for dir in kubernetes/apps/*/*/; do
  dir=${dir%/}
  app=$(basename "$dir")
  if [ -f "$dir/kustomization.yaml" ]; then
    echo "== $app (kustomize)"
    kustomize build "$dir" > "$out/$app.yaml"
    continue
  fi
  [ -f "$dir/Chart.yaml" ] || continue
  name=$(awk '/^  name:/ { print $2; exit }' "$dir/application.yaml")
  ns=$(awk '/^    namespace:/ { print $2; exit }' "$dir/application.yaml")
  [ -n "$name" ] && [ -n "$ns" ] || { echo "::error::$dir/application.yaml: no name or destination namespace"; exit 1; }
  echo "== $app (release $name, namespace $ns)"
  helm dependency build "$dir" > /dev/null
  helm lint "$dir"
  helm template "$name" "$dir" --namespace "$ns" --include-crds > "$out/$app.yaml"
done
