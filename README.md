# Kubernetes Store Provisioning Platform

A production-ready platform for provisioning on-demand WooCommerce e-commerce stores on Kubernetes. Each store runs as isolated resources in its own namespace with complete lifecycle management.

**Built for the Urumi AI SDE Internship Assignment**

## Architecture

```
┌─────────────────┐      ┌──────────────┐      ┌─────────────────┐
│ React Dashboard │─────▶│  Flask API   │─────▶│  Store CRD      │
│  (Frontend)     │      │  (Backend)   │      │  (Kubernetes)   │
└─────────────────┘      └──────────────┘      └─────────────────┘
                                                          │
                                                          ▼
                                                 ┌─────────────────┐
                                                 │ kopf Controller │
                                                 │  (Python)       │
                                                 └─────────────────┘
                                                          │
                                                          ▼
                                                 ┌─────────────────┐
                                                 │   Helm Install  │
                                                 │  (store-chart)  │
                                                 └─────────────────┘
                                                          │
                          ┌───────────────────────────────┼───────────────────────────────┐
                          ▼                               ▼                               ▼
                 ┌──────────────────┐          ┌──────────────────┐          ┌──────────────────┐
                 │ Store Namespace  │          │ Store Namespace  │          │ Store Namespace  │
                 │  store-shop1     │          │  store-shop2     │          │  store-shop3     │
                 │                  │          │                  │          │                  │
                 │ ┌──────────────┐ │          │ ┌──────────────┐ │          │ ┌──────────────┐ │
                 │ │  WordPress   │ │          │ │  WordPress   │ │          │ │  WordPress   │ │
                 │ │ + WooCommerce│ │          │ │ + WooCommerce│ │          │ │ + WooCommerce│ │
                 │ └──────────────┘ │          │ └──────────────┘ │          │ └──────────────┘ │
                 │ ┌──────────────┐ │          │ ┌──────────────┐ │          │ ┌──────────────┐ │
                 │ │   MariaDB    │ │          │ │   MariaDB    │ │          │ │   MariaDB    │ │
                 │ └──────────────┘ │          │ └──────────────┘ │          │ └──────────────┘ │
                 │ ┌──────────────┐ │          │ ┌──────────────┐ │          │ ┌──────────────┐ │
                 │ │   Ingress    │ │          │ │   Ingress    │ │          │ │   Ingress    │ │
                 │ └──────────────┘ │          │ └──────────────┘ │          │ └──────────────┘ │
                 └──────────────────┘          └──────────────────┘          └──────────────────┘
                    shop1.local.store             shop2.local.store             shop3.local.store
```

## Features

- **On-Demand Provisioning**: Create WooCommerce stores via API in seconds
- **Complete Isolation**: Each store runs in its own namespace with NetworkPolicies
- **Resource Management**: ResourceQuotas and LimitRanges per store
- **Automated Setup**: WordPress + WooCommerce installation, sample products, payment gateways
- **Production Ready**: Helm charts for local (Kind) and production (k3s) deployments
- **Idempotent Operations**: Helm lookup for secret persistence, resumable controller logic
- **Lifecycle Management**: Create, monitor, and delete stores via Kubernetes native CRDs
- **Modern UI**: Dark-themed React dashboard with real-time updates

## Components

### Platform Components (platform-chart)
- **Flask API**: REST API for store management (CRUD operations)
- **React Dashboard**: Web UI for creating and managing stores
- **kopf Controller**: Kubernetes operator that watches Store CRDs and provisions infrastructure

### Store Components (store-chart)
Each store includes:
- **WordPress 6.4 + WooCommerce**: E-commerce application
- **MariaDB 10.11**: Database with persistent storage
- **NGINX Ingress**: External access with custom subdomain
- **Setup Job**: Automated WooCommerce installation with sample products
- **Security**: NetworkPolicy (default deny), ResourceQuota, LimitRange
- **Isolation**: Dedicated namespace per store

## Prerequisites

- **Docker**: For building container images (v24+)
- **kubectl**: Kubernetes CLI (v1.27+)
- **Helm**: Package manager (v3.12+)
- **Kind**: Local Kubernetes clusters (v0.20+) - for development only
- **Git**: Version control
- **Bash**: For running setup scripts (Linux/Mac/WSL on Windows)

Optional:
- **Node.js 20+**: Only needed for frontend development (not for deployment)

## Quick Start (5 Minutes)

### 1. One-Command Setup

```bash
# Clone the repository
git clone <repo-url>
cd store-platform

# Run the complete setup script
./setup-cluster.sh
```

This script will:
1. ✅ Create a Kind cluster with ingress support
2. ✅ Install NGINX ingress controller
3. ✅ Build all Docker images (API, controller, dashboard)
4. ✅ Load images into Kind
5. ✅ Install the platform chart with all components
6. ✅ Wait for everything to be ready

**Total time: ~3-5 minutes**

### 2. Add DNS Entries

```bash
# Option 1: Use the helper script (requires sudo)
sudo bash add-hosts.sh

# Option 2: Manually add to /etc/hosts (Linux/Mac) or C:\Windows\System32\drivers\etc\hosts (Windows)
127.0.0.1 dashboard.local.store api.local.store
```

### 3. Access the Dashboard

Open your browser and navigate to:

🌐 **http://dashboard.local.store**

You should see the Store Platform Dashboard with a dark theme!

### 4. Create Your First Store

1. Click **"+ Create Store"** button
2. Enter a store name (e.g., "My Test Shop")
3. Select **WooCommerce** (Medusa coming soon)
4. Click **"Create Store"**
5. Wait ~1-2 minutes for provisioning (watch the status change)
6. Once status is **"Ready"**, click the store URL

### 5. Set Up DNS for Store URLs (Important!)

Individual stores get their own subdomain (e.g., `myshop-abc123.local.store`). You have two options:

#### Option A: dnsmasq (Recommended - Wildcard DNS)

**On macOS:**
```bash
# Install dnsmasq
brew install dnsmasq

# Configure wildcard for .local.store
echo 'address=/local.store/127.0.0.1' >> $(brew --prefix)/etc/dnsmasq.conf

# Start dnsmasq
sudo brew services start dnsmasq

# Configure macOS to use dnsmasq for .local.store
sudo mkdir -p /etc/resolver
echo "nameserver 127.0.0.1" | sudo tee /etc/resolver/local.store

# Test
ping mystore-abc123.local.store  # Should resolve to 127.0.0.1
```

**On Linux:**
```bash
# Install dnsmasq
sudo apt-get update && sudo apt-get install dnsmasq

# Configure wildcard for .local.store
echo 'address=/local.store/127.0.0.1' | sudo tee -a /etc/dnsmasq.conf

# Restart dnsmasq
sudo systemctl restart dnsmasq

# Configure NetworkManager to use dnsmasq
echo "[main]
dns=dnsmasq" | sudo tee /etc/NetworkManager/NetworkManager.conf

# Restart NetworkManager
sudo systemctl restart NetworkManager
```

#### Option B: Manual /etc/hosts Entries

After creating each store, add its URL to `/etc/hosts`:

```bash
# Get the store ID from the dashboard
127.0.0.1 myshop-abc123.local.store
```

This is tedious but works if you only have a few stores.

### 6. Access Your Store

Once the store status is **"Ready"**, you can:

**Visit the store frontend:**
```
http://<store-id>.local.store
```

**Access WordPress admin:**
```
URL: http://<store-id>.local.store/wp-admin
Username: admin
Password: [Get from dashboard or run command below]
```

**Get WordPress admin password:**
```bash
# Find your store ID from the dashboard, then run:
kubectl get secret -n store-<store-id> <store-id>-wordpress -o jsonpath='{.data.admin-password}' | base64 -d
```

### 7. Place a Test Order

1. Visit your store: `http://<store-id>.local.store`
2. Click on "Sample T-Shirt" product
3. Click "Add to Cart"
4. Click "View Cart" → "Proceed to Checkout"
5. Fill in billing details (use any test data)
6. Select "Cash on Delivery" payment method
7. Click "Place Order"
8. ✅ Order complete! Check WooCommerce admin to see the order.

### 8. Delete a Store

From the dashboard:
1. Click the **"Delete"** button on any store card
2. Confirm deletion
3. The controller will clean up all resources (namespace, PVCs, secrets)

## Project Structure

```
store-platform/
├── setup-cluster.sh                   # One-command setup script
├── teardown.sh                        # Complete cleanup script
├── add-hosts.sh                       # Helper to add DNS entries
├── README.md                          # This file
│
├── platform-chart/                    # Helm chart for platform
│   ├── Chart.yaml
│   ├── values.yaml                    # Default values
│   ├── values-local.yaml              # Local development (Kind)
│   ├── values-prod.yaml               # Production (k3s)
│   └── templates/
│       ├── _helpers.tpl
│       ├── store-crd.yaml             # Store Custom Resource Definition
│       ├── platform-namespace.yaml
│       ├── controller-rbac.yaml       # ServiceAccount + ClusterRole + Binding
│       ├── controller-deployment.yaml
│       ├── api-deployment.yaml
│       ├── api-service.yaml
│       ├── dashboard-deployment.yaml
│       ├── dashboard-service.yaml
│       └── ingress.yaml
│
├── store-chart/                       # Helm chart for per-store resources
│   ├── Chart.yaml
│   ├── values.yaml
│   └── templates/
│       ├── _helpers.tpl
│       ├── namespace.yaml             # Store-specific namespace
│       ├── mariadb-secret.yaml        # Idempotent password generation
│       ├── mariadb-pvc.yaml
│       ├── mariadb-statefulset.yaml
│       ├── mariadb-service.yaml
│       ├── wordpress-secret.yaml
│       ├── wordpress-deployment.yaml
│       ├── wordpress-service.yaml
│       ├── wordpress-setup-job.yaml   # WooCommerce installation
│       ├── wordpress-ingress.yaml
│       ├── resource-quota.yaml        # CPU/memory/storage limits
│       ├── limit-range.yaml
│       └── network-policy.yaml        # Default deny + explicit rules
│
├── backend/                           # Flask API
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── app.py                         # REST API endpoints
│   └── config.py                      # Configuration
│
├── controller/                        # kopf-based Kubernetes operator
│   ├── Dockerfile                     # Includes store-chart baked in
│   ├── requirements.txt
│   └── controller.py                  # Operator handlers (@kopf.on.create, etc.)
│
├── frontend/                          # React dashboard
│   ├── Dockerfile                     # Multi-stage: build + nginx
│   ├── nginx.conf                     # SPA routing config
│   ├── package.json
│   ├── vite.config.js
│   ├── index.html
│   └── src/
│       ├── main.jsx
│       ├── App.jsx                    # Main app with auto-refresh
│       ├── App.css                    # Dark theme styles
│       ├── index.css
│       ├── api.js                     # API client (axios)
│       └── components/
│           ├── StoreList.jsx
│           ├── StoreCard.jsx          # Status badges, delete confirmation
│           └── CreateStoreModal.jsx   # Form with validation
│
└── docs/
    └── system-design.md               # Detailed architecture documentation
```

## Development & Debugging

### View Logs

```bash
# Controller logs (watch store provisioning)
kubectl logs -n store-platform -l app=store-controller -f

# API logs
kubectl logs -n store-platform -l app=platform-api -f

# Dashboard logs
kubectl logs -n store-platform -l app=platform-dashboard -f
```

### Check Store Status

```bash
# List all stores
kubectl get stores -n store-platform

# Describe a specific store
kubectl describe store <store-name> -n store-platform

# Check store resources
kubectl get all -n store-<store-id>
```

### Debug Store Provisioning

```bash
# Check WordPress setup job logs
kubectl logs -n store-<store-id> job/<store-id>-wordpress-setup

# Check WordPress pod
kubectl logs -n store-<store-id> -l app.kubernetes.io/component=wordpress

# Check MariaDB pod
kubectl logs -n store-<store-id> -l app.kubernetes.io/component=mariadb

# Exec into WordPress container
kubectl exec -it -n store-<store-id> <wordpress-pod-name> -- bash
```

### Test API Directly

```bash
# Health check
curl http://api.local.store/api/health

# List all stores
curl http://api.local.store/api/stores

# Get specific store
curl http://api.local.store/api/stores/<store-id>

# Create store via API
curl -X POST http://api.local.store/api/stores \
  -H "Content-Type: application/json" \
  -d '{"displayName": "My API Store", "storeType": "woocommerce"}'

# Delete store
curl -X DELETE http://api.local.store/api/stores/<store-id>
```

### Rebuild Images

If you make changes to the code:

```bash
# Rebuild specific component
docker build -t store-platform-api:local ./backend
kind load docker-image store-platform-api:local --name store-platform

# Restart deployment to use new image
kubectl rollout restart deployment/platform-api -n store-platform

# Or rebuild all and redeploy
./setup-cluster.sh  # Will detect existing cluster and offer to recreate
```

### Test Store Chart Directly

```bash
# Install store chart directly (bypass controller)
helm install test-store ./store-chart \
  --namespace store-test \
  --create-namespace \
  --set storeId=test-store \
  --set storeType=woocommerce \
  --set baseDomain=local.store \
  --set displayName="Test Store"

# Watch provisioning
kubectl get pods -n store-test -w

# Clean up
helm uninstall test-store -n store-test
kubectl delete namespace store-test
```

## Production Deployment (k3s on VPS)

### Prerequisites

1. VPS with Ubuntu 22.04+ (4GB RAM, 2 CPUs minimum)
2. Domain name with DNS configured
3. Container registry (Docker Hub, GitHub Container Registry, etc.)

### Steps

#### 1. Install k3s

```bash
# On your VPS
curl -sfL https://get.k3s.io | sh -

# Verify
sudo k3s kubectl get nodes
```

#### 2. Build and Push Images

```bash
# On your local machine
# Set your registry
REGISTRY="ghcr.io/yourusername"

# Build and tag
docker build -t ${REGISTRY}/store-platform-api:v1.0.0 ./backend
docker build -t ${REGISTRY}/store-platform-controller:v1.0.0 ./controller
docker build -t ${REGISTRY}/store-platform-dashboard:v1.0.0 ./frontend

# Push to registry
docker push ${REGISTRY}/store-platform-api:v1.0.0
docker push ${REGISTRY}/store-platform-controller:v1.0.0
docker push ${REGISTRY}/store-platform-dashboard:v1.0.0
```

#### 3. Configure values-prod.yaml

Edit `platform-chart/values-prod.yaml`:

```yaml
baseDomain: yourdomain.com
api:
  image:
    repository: ghcr.io/yourusername/store-platform-api
    tag: v1.0.0
# ... update other image repositories and domain references
```

#### 4. Install Platform

```bash
# Copy kubeconfig from VPS
scp root@your-vps:/etc/rancher/k3s/k3s.yaml ~/.kube/k3s-config
export KUBECONFIG=~/.kube/k3s-config

# Install platform
helm install store-platform ./platform-chart \
  -f ./platform-chart/values-prod.yaml \
  --namespace store-platform \
  --create-namespace
```

#### 5. Configure DNS

Add wildcard DNS records:

```
A    dashboard.yourdomain.com    <VPS-IP>
A    api.yourdomain.com          <VPS-IP>
A    *.yourdomain.com            <VPS-IP>
```

#### 6. (Optional) Set Up TLS with cert-manager

```bash
# Install cert-manager
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml

# Create ClusterIssuer
kubectl apply -f - <<EOF
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: your-email@example.com
    privateKeySecretRef:
      name: letsencrypt-prod
    solvers:
    - http01:
        ingress:
          class: nginx
EOF

# Update values-prod.yaml to enable cert-manager annotations
# Then upgrade the release
helm upgrade store-platform ./platform-chart -f ./platform-chart/values-prod.yaml
```

## Cleanup

### Delete Everything

```bash
# Run teardown script
./teardown.sh
```

This will:
- Uninstall platform Helm release
- Delete all store namespaces
- Delete platform namespace
- Delete Kind cluster

### Selective Cleanup

```bash
# Delete only stores (keep platform running)
kubectl delete stores --all -n store-platform

# Delete specific store
kubectl delete store <store-name> -n store-platform

# Uninstall platform but keep cluster
helm uninstall store-platform -n store-platform
```

## Troubleshooting

### Setup script fails

```bash
# Check Docker is running
docker ps

# Check Kind cluster
kind get clusters

# Check kubectl context
kubectl config current-context
```

### Platform pods not starting

```bash
# Check events
kubectl get events -n store-platform --sort-by='.lastTimestamp'

# Check pod status
kubectl describe pod <pod-name> -n store-platform

# Check if images are loaded
docker images | grep store-platform
```

### Store stuck in "Provisioning"

```bash
# Check controller logs
kubectl logs -n store-platform -l app=store-controller --tail=100

# Check Store status
kubectl describe store <store-name> -n store-platform

# Check if Helm release exists
helm list -A | grep <store-id>
```

### Cannot access store URL

```bash
# Check ingress
kubectl get ingress -n store-<store-id>
kubectl describe ingress <store-id>-wordpress -n store-<store-id>

# Check DNS resolution
ping <store-id>.local.store

# Check NGINX ingress controller
kubectl get pods -n ingress-nginx
kubectl logs -n ingress-nginx <ingress-controller-pod>
```

### WordPress setup job fails

```bash
# Check job status
kubectl get jobs -n store-<store-id>

# Check job logs
kubectl logs -n store-<store-id> job/<store-id>-wordpress-setup

# Common issues:
# - WordPress not responding: Wait longer, WordPress takes time to start
# - Database connection: Check MariaDB pod status
# - WP-CLI errors: Check WordPress pod logs
```

## Architecture Decisions

See [docs/system-design.md](docs/system-design.md) for comprehensive documentation on:

- Detailed component architecture
- Idempotency guarantees (Helm lookup, controller resume logic)
- Failure handling and recovery
- Security model (RBAC, NetworkPolicy, resource limits)
- Scaling considerations
- Local vs production differences
- Abuse prevention mechanisms

## Resource Limits

### Per Store
- **Pods**: Maximum 4
- **CPU**: 1 core requested, 2 cores limit
- **Memory**: 2Gi requested, 3Gi limit
- **Storage**: 5Gi total

### Default Container Limits
- **WordPress**: 256Mi/200m CPU (limit: 512Mi/500m)
- **MariaDB**: 128Mi/100m CPU (limit: 512Mi/500m)

### Platform Components
- **API**: 128Mi/100m CPU (limit: 512Mi/500m)
- **Dashboard**: 64Mi/50m CPU (limit: 256Mi/200m)
- **Controller**: 256Mi/200m CPU (limit: 1Gi/1000m)

## API Reference

### Endpoints

```
GET    /api/health              Health check
GET    /api/stores              List all stores
GET    /api/stores/<id>         Get specific store
POST   /api/stores              Create new store
DELETE /api/stores/<id>         Delete store
```

### Create Store Request

```json
POST /api/stores
{
  "displayName": "My Store",
  "storeType": "woocommerce"
}
```

Response (201):
```json
{
  "id": "my-store-abc123",
  "displayName": "My Store",
  "storeType": "woocommerce",
  "phase": "Provisioning",
  "url": null,
  "adminUrl": null,
  "createdAt": "2024-01-15T10:30:00Z",
  "readyAt": null,
  "events": []
}
```

## Demo Video Checklist

✅ Show dashboard dark theme
✅ Create store from UI
✅ Watch status change from Provisioning → Installing → Configuring → Ready
✅ Click store URL and show WooCommerce storefront
✅ Log into WordPress admin
✅ Show sample product
✅ Place test order
✅ Delete store and show cleanup

## License

MIT

## Author

Built for the Urumi AI SDE Internship Assignment.

For detailed architecture and design decisions, see [docs/system-design.md](docs/system-design.md).
