#!/bin/sh
# usage: .github/scripts/render-charts.sh <out dir>   (run from the repo root; needs helm)
# Builds, lints and renders every app chart the way ArgoCD does: release name and
# namespace come from the app's application.yaml. Output: <out dir>/<app dir name>.yaml
set -eu
out=$1
mkdir -p "$out"
for dir in kubernetes/apps/*/*/; do
  dir=${dir%/}
  [ -f "$dir/Chart.yaml" ] || continue
  app=$(basename "$dir")
  name=$(awk '/^  name:/ { print $2; exit }' "$dir/application.yaml")
  ns=$(awk '/^    namespace:/ { print $2; exit }' "$dir/application.yaml")
  [ -n "$name" ] && [ -n "$ns" ] || { echo "::error::$dir/application.yaml: no name or destination namespace"; exit 1; }
  echo "== $app (release $name, namespace $ns)"
  helm dependency build "$dir" > /dev/null
  helm lint "$dir"
  helm template "$name" "$dir" --namespace "$ns" --include-crds > "$out/$app.yaml"
done
