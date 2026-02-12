#!/bin/bash

# teardown.sh
# Completely removes the store platform and all stores
# Use with caution - this deletes everything!

set -euo pipefail

CLUSTER_NAME="store-platform"

echo "==================================="
echo "Store Platform Teardown"
echo "==================================="
echo ""
echo "⚠️  WARNING: This will delete:"
echo "  • The platform chart and all platform pods"
echo "  • ALL store namespaces and stores"
echo "  • The entire Kind cluster (if using Kind)"
echo ""
read -p "Are you sure you want to continue? (yes/no) " -r
echo

if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
    echo "❌ Teardown cancelled."
    exit 0
fi

echo "🗑️  Starting teardown..."
echo ""

# Step 1: Uninstall platform chart
echo "📦 Step 1/4: Uninstalling platform chart..."
if helm list -n store-platform 2>/dev/null | grep -q store-platform; then
    helm uninstall store-platform -n store-platform --wait
    echo "✅ Platform chart uninstalled"
else
    echo "ℹ️  Platform chart not found (may already be uninstalled)"
fi
echo ""

# Step 2: Delete all store namespaces
echo "🏪 Step 2/4: Deleting all store namespaces..."
STORE_NAMESPACES=$(kubectl get namespaces -l platform.urumi.io/managed-by=store-platform -o name 2>/dev/null || true)

if [ -n "$STORE_NAMESPACES" ]; then
    echo "Found store namespaces:"
    echo "$STORE_NAMESPACES"
    echo ""

    for ns in $STORE_NAMESPACES; do
        echo "  → Deleting $ns..."
        kubectl delete "$ns" --wait=false
    done

    echo "⏳ Waiting for namespaces to be deleted..."
    for ns in $STORE_NAMESPACES; do
        kubectl wait --for=delete "$ns" --timeout=60s 2>/dev/null || true
    done

    echo "✅ All store namespaces deleted"
else
    echo "ℹ️  No store namespaces found"
fi
echo ""

# Step 3: Delete platform namespace
echo "📋 Step 3/4: Deleting platform namespace..."
if kubectl get namespace store-platform >/dev/null 2>&1; then
    kubectl delete namespace store-platform --wait
    echo "✅ Platform namespace deleted"
else
    echo "ℹ️  Platform namespace not found"
fi
echo ""

# Step 4: Delete Kind cluster (if it exists)
echo "🐳 Step 4/4: Deleting Kind cluster..."
if kind get clusters 2>/dev/null | grep -q "^${CLUSTER_NAME}$"; then
    kind delete cluster --name "${CLUSTER_NAME}"
    echo "✅ Kind cluster deleted"
else
    echo "ℹ️  Kind cluster '${CLUSTER_NAME}' not found"
fi
echo ""

echo "==================================="
echo "✅ Teardown Complete!"
echo "==================================="
echo ""
echo "All resources have been cleaned up."
echo ""
echo "To start fresh:"
echo "  ./setup-cluster.sh"
echo ""
