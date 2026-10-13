#!/bin/sh
# usage: render_all.sh <out dir>   (run from repo root; needs the scratchpad helm + vendored charts)
set -eu
SP=/tmp/claude-0/-home-user/157599aa-d70a-574a-83f6-622182f1113f/scratchpad
A=kubernetes/apps/infrastructure; O=$1; mkdir -p "$O"
$SP/render2.sh $A/longhorn longhorn longhorn-system "$O/longhorn.yaml" longhorn-1.8.2.tgz
$SP/render2.sh $A/traefik traefik traefik "$O/traefik.yaml" traefik-32.1.1.tgz
$SP/render2.sh $A/adguard-home adguard-home adguard "$O/adguard.yaml"
if [ -d $A/ingress-auth ]; then $SP/render2.sh $A/ingress-auth ingress-auth traefik "$O/ingress-auth.yaml"; else : > "$O/ingress-auth.yaml"; fi
