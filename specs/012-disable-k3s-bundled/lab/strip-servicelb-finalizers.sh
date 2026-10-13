#!/bin/sh
# Remove ServiceLB's load-balancer-cleanup finalizer from every LoadBalancer Service.
# Only run after k3s restarted with servicelb disabled (otherwise ServiceLB re-adds it).
set -eu
kubectl get svc -A -o jsonpath='{range .items[?(@.spec.type=="LoadBalancer")]}{.metadata.namespace}{" "}{.metadata.name}{"\n"}{end}' |
while read -r ns name; do
  kubectl -n "$ns" get svc "$name" -o jsonpath='{.metadata.finalizers}' | grep -q load-balancer-cleanup || continue
  kubectl -n "$ns" patch svc "$name" --type=json \
    -p '[{"op":"remove","path":"/metadata/finalizers"}]'
done
