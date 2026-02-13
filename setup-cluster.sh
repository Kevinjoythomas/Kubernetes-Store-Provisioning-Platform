#!/bin/bash

# setup-cluster.sh
# Complete one-command setup for local development
# Creates Kind cluster, builds images, deploys platform

set -euo pipefail

CLUSTER_NAME="store-platform"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "==================================="
echo "Store Platform Cluster Setup"
echo "==================================="
echo ""

# Check prerequisites
echo "Checking prerequisites..."
command -v kind >/dev/null 2>&1 || { echo "Error: kind is not installed. Please install Kind from https://kind.sigs.k8s.io/"; exit 1; }
command -v kubectl >/dev/null 2>&1 || { echo "Error: kubectl is not installed."; exit 1; }
command -v helm >/dev/null 2>&1 || { echo "Error: helm is not installed."; exit 1; }
command -v docker >/dev/null 2>&1 || { echo "Error: docker is not installed."; exit 1; }
echo "All prerequisites found"
echo ""

# Check if cluster already exists
if kind get clusters 2>/dev/null | grep -q "^${CLUSTER_NAME}$"; then
    echo "Cluster '${CLUSTER_NAME}' already exists."
    read -p "Do you want to delete and recreate it? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Deleting existing cluster..."
        kind delete cluster --name "${CLUSTER_NAME}"
    else
        echo "Aborted. Using existing cluster."
        exit 0
    fi
fi

echo "Step 1/6: Creating Kind cluster with ingress support..."

# Create Kind cluster with extraPortMappings for ingress
cat <<EOF | kind create cluster --name "${CLUSTER_NAME}" --config=-
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
nodes:
- role: control-plane
  kubeadmConfigPatches:
  - |
    kind: InitConfiguration
    nodeRegistration:
      kubeletExtraArgs:
        node-labels: "ingress-ready=true"
  extraPortMappings:
  - containerPort: 80
    hostPort: 80
    protocol: TCP
  - containerPort: 443
    hostPort: 443
    protocol: TCP
EOF

echo "Kind cluster created successfully"
echo ""

# Set kubectl context
kubectl cluster-info --context "kind-${CLUSTER_NAME}"
echo ""

echo "Step 2/6: Installing NGINX Ingress Controller..."

# Install NGINX ingress controller (Kind-specific manifest)
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/kind/deploy.yaml

echo "Waiting for NGINX Ingress Controller to be ready..."

# Wait for the ingress controller to be ready (timeout 5 minutes)
kubectl wait --namespace ingress-nginx \
  --for=condition=ready pod \
  --selector=app.kubernetes.io/component=controller \
  --timeout=300s

echo "NGINX Ingress Controller is ready"
echo ""

# Label namespaces for NetworkPolicy
echo "Labeling namespaces for NetworkPolicy..."
kubectl label namespace ingress-nginx name=ingress-nginx --overwrite
kubectl label namespace kube-system name=kube-system --overwrite
echo "Namespaces labeled"
echo ""

echo "Step 3/6: Building Docker images..."

# Build backend image
echo "  Building backend API image..."
docker build -t store-platform-api:local "${SCRIPT_DIR}/backend" -q
echo "    store-platform-api:local built"

# Copy store-chart into controller directory for Docker build context
echo "  Copying store-chart into controller build context..."
cp -r "${SCRIPT_DIR}/store-chart" "${SCRIPT_DIR}/controller/store-chart"

# Build controller image
echo "  Building controller image..."
docker build -t store-platform-controller:local "${SCRIPT_DIR}/controller" -q
echo "    store-platform-controller:local built"

# Clean up copied store-chart
rm -rf "${SCRIPT_DIR}/controller/store-chart"

# Build frontend image
echo "  Building frontend dashboard image..."
docker build -t store-platform-dashboard:local "${SCRIPT_DIR}/frontend" -q
echo "    store-platform-dashboard:local built"

echo "All images built successfully"
echo ""

echo "Step 4/6: Loading images into Kind cluster..."

# Load images into Kind
kind load docker-image store-platform-api:local --name "${CLUSTER_NAME}"
echo "  store-platform-api:local loaded"

kind load docker-image store-platform-controller:local --name "${CLUSTER_NAME}"
echo "  store-platform-controller:local loaded"

kind load docker-image store-platform-dashboard:local --name "${CLUSTER_NAME}"
echo "  store-platform-dashboard:local loaded"

echo "All images loaded into Kind"
echo ""

echo "Step 5/6: Installing platform chart (includes CRD)..."

# Install platform chart (CRD is created by the chart via storeCRD.create=true)
helm install store-platform "${SCRIPT_DIR}/platform-chart" \
  -f "${SCRIPT_DIR}/platform-chart/values-local.yaml" \
  --create-namespace \
  --namespace store-platform \
  --wait \
  --timeout 5m

echo "Platform chart installed"
echo ""

echo "Step 6/6: Waiting for all platform pods to be ready..."

# Wait for all pods in store-platform namespace
kubectl wait --namespace store-platform \
  --for=condition=ready pod \
  --all \
  --timeout=300s

echo "All platform pods are ready"
echo ""

echo "==================================="
echo "Setup Complete!"
echo "==================================="
echo ""
echo "Cluster Status:"
kubectl get pods -n store-platform
echo ""

echo "==================================="
echo "Next Steps"
echo "==================================="
echo ""
echo "1. Add DNS entries to your /etc/hosts file:"
echo ""
echo "   sudo bash add-hosts.sh"
echo ""
echo "   Or manually add these lines to /etc/hosts:"
echo "   127.0.0.1 dashboard.local.store api.local.store"
echo ""
echo "2. Access the dashboard:"
echo "   http://dashboard.local.store"
echo ""
echo "3. Create your first store from the dashboard!"
echo ""
echo "Important Notes:"
echo ""
echo "  For store URLs (e.g., mystore-abc123.local.store), you need wildcard DNS:"
echo ""
echo "  Option A: Use dnsmasq (recommended)"
echo "    See: docs/LOCAL_DNS_SETUP.md"
echo ""
echo "  Option B: Manually add each store to /etc/hosts"
echo "    127.0.0.1 mystore-abc123.local.store"
echo ""
echo "  API health check: curl http://api.local.store/api/health"
echo "  View logs: kubectl logs -n store-platform -l app=store-controller -f"
echo "  Teardown: ./teardown.sh"
echo ""
echo "==================================="
echo ""
