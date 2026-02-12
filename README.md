# Kubernetes Store Provisioning Platform

A production-ready platform for provisioning on-demand WooCommerce e-commerce stores on Kubernetes. Each store runs as isolated resources in its own namespace with complete lifecycle management.

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
- **Lifecycle Management**: Create, monitor, and delete stores via Kubernetes native CRDs

## Components

### Platform Components (platform-chart)
- **Flask API**: REST API for store management
- **React Dashboard**: Web UI for creating and managing stores
- **kopf Controller**: Kubernetes operator that watches Store CRDs and provisions infrastructure

### Store Components (store-chart)
Each store includes:
- **WordPress 6.4 + WooCommerce**: E-commerce application
- **MariaDB 10.11**: Database with persistence
- **NGINX Ingress**: External access with custom subdomain
- **Setup Job**: Automated WooCommerce installation and configuration
- **Security**: NetworkPolicy, ResourceQuota, LimitRange

## Prerequisites

- **Docker**: For building container images
- **kubectl**: Kubernetes CLI (v1.27+)
- **Helm**: Package manager (v3.12+)
- **Kind**: Local Kubernetes clusters (v0.20+) - for development
- **Git**: Version control

## Quick Start

### 1. Setup Local Cluster

```bash
# Create Kind cluster with NGINX ingress
./setup-cluster.sh

# Verify cluster is ready
kubectl cluster-info
kubectl get pods -n ingress-nginx
```

### 2. Install Platform Components

```bash
# Install the platform (API, Dashboard, Controller)
helm install platform ./platform-chart \
  -f ./platform-chart/values-local.yaml \
  --create-namespace \
  --namespace platform

# Verify platform is running
kubectl get pods -n platform
kubectl get crd stores.platform.urumi.io
```

### 3. Create a Test Store Manually

```bash
# Create a Store CRD
kubectl apply -f - <<EOF
apiVersion: platform.urumi.io/v1
kind: Store
metadata:
  name: demo-store
  namespace: platform
spec:
  storeType: woocommerce
  displayName: "Demo Store"
  baseDomain: local.store
EOF

# Watch the store being provisioned
kubectl get stores -n platform -w
```

### 4. Test Store Chart Directly (Optional)

```bash
# Install a store directly using Helm (bypassing controller)
helm install test-store ./store-chart \
  --namespace store-test \
  --create-namespace \
  --set storeId=test \
  --set storeType=woocommerce \
  --set baseDomain=local.store \
  --set displayName="Test Store"

# Watch resources being created
kubectl get all -n store-test

# Check the setup job
kubectl logs -n store-test job/test-store-wordpress-setup

# Wait for WordPress to be ready
kubectl wait --for=condition=ready pod -l app.kubernetes.io/component=wordpress -n store-test --timeout=300s
```

### 5. Access the Store

Add to your `/etc/hosts` (Linux/Mac) or `C:\Windows\System32\drivers\etc\hosts` (Windows):

```
127.0.0.1 test.local.store
127.0.0.1 dashboard.local.store
127.0.0.1 api.local.store
```

Then visit:
- **Store**: http://test.local.store
- **WordPress Admin**: http://test.local.store/wp-admin
  - Username: `admin`
  - Password: Get from secret: `kubectl get secret -n store-test test-store-wordpress -o jsonpath='{.data.admin-password}' | base64 -d`

## Development Workflow

### Project Structure

```
store-platform/
├── README.md                          # This file
├── setup-cluster.sh                   # Kind cluster setup
├── platform-chart/                    # Helm chart for platform components
│   ├── Chart.yaml
│   ├── values.yaml                    # Default values
│   ├── values-local.yaml              # Local development overrides
│   ├── values-prod.yaml               # Production overrides
│   └── templates/                     # Kubernetes manifests
│       ├── _helpers.tpl
│       ├── store-crd.yaml             # Custom Resource Definition
│       ├── controller-rbac.yaml       # ServiceAccount, ClusterRole, Binding
│       ├── controller-deployment.yaml
│       ├── api-deployment.yaml
│       ├── api-service.yaml
│       ├── dashboard-deployment.yaml
│       ├── dashboard-service.yaml
│       ├── ingress.yaml
│       └── platform-namespace.yaml
├── store-chart/                       # Helm chart for individual stores
│   ├── Chart.yaml
│   ├── values.yaml
│   └── templates/                     # Per-store resources
│       ├── _helpers.tpl
│       ├── namespace.yaml             # Store-specific namespace
│       ├── mariadb-secret.yaml        # Database credentials
│       ├── mariadb-pvc.yaml
│       ├── mariadb-statefulset.yaml
│       ├── mariadb-service.yaml
│       ├── wordpress-secret.yaml      # WordPress admin credentials
│       ├── wordpress-deployment.yaml
│       ├── wordpress-service.yaml
│       ├── wordpress-setup-job.yaml   # WooCommerce installation
│       ├── wordpress-ingress.yaml
│       ├── resource-quota.yaml        # Resource limits per store
│       ├── limit-range.yaml
│       └── network-policy.yaml        # Network isolation
├── backend/                           # Flask API
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── app.py                         # API implementation
│   └── config.py
├── controller/                        # kopf-based controller
│   ├── Dockerfile
│   ├── requirements.txt
│   └── controller.py                  # Operator logic
├── frontend/                          # React dashboard
│   ├── Dockerfile
│   ├── package.json
│   ├── vite.config.js
│   ├── index.html
│   └── src/
│       ├── App.jsx
│       ├── main.jsx
│       ├── api.js                     # API client
│       └── components/
│           ├── StoreList.jsx
│           ├── StoreCard.jsx
│           └── CreateStoreModal.jsx
└── docs/
    └── system-design.md               # Detailed architecture
```

### Building Application Images

```bash
# Backend API
cd backend
docker build -t store-platform-api:latest .

# Controller
cd controller
docker build -t store-platform-controller:latest .

# Frontend
cd frontend
docker build -t store-platform-dashboard:latest .
```

### Debugging

```bash
# Check controller logs
kubectl logs -n platform deployment/platform-controller -f

# Check API logs
kubectl logs -n platform deployment/platform-api -f

# Check store provisioning status
kubectl describe store <store-name> -n platform

# Check store resources
kubectl get all -n store-<store-id>

# Debug WordPress setup
kubectl logs -n store-<store-id> job/<store-id>-wordpress-setup

# Check NetworkPolicy
kubectl describe networkpolicy -n store-<store-id>

# Check ResourceQuota
kubectl describe resourcequota -n store-<store-id>
```

### Testing Store Isolation

```bash
# Try to access MariaDB from outside namespace (should fail)
kubectl run -it --rm debug --image=mysql:8.0 --restart=Never -- \
  mysql -h test-store-mariadb.store-test.svc.cluster.local -u woocommerce -p

# This should timeout due to NetworkPolicy
```

## Production Deployment

For production deployment on k3s:

```bash
# Use production values
helm install platform ./platform-chart \
  -f ./platform-chart/values-prod.yaml \
  --namespace platform \
  --create-namespace

# Update baseDomain in values-prod.yaml to your actual domain
# Configure external DNS for wildcard subdomain (*.yourdomain.com)
# Set up TLS certificates via cert-manager (optional)
```

## Store Lifecycle

1. **Create**: User submits store request via Dashboard/API
2. **Provision**: Controller creates namespace, installs Helm chart
3. **Install**: WordPress setup Job installs WooCommerce, creates sample products
4. **Ready**: Store is accessible via ingress, status updated
5. **Monitor**: Controller periodically checks store health
6. **Delete**: User deletes store, controller runs cleanup

## Security Features

- **Namespace Isolation**: Each store in separate namespace
- **NetworkPolicy**: Default deny, explicit allow rules
- **ResourceQuota**: Prevent resource exhaustion
- **Secrets Management**: Passwords generated securely
- **RBAC**: Controller has minimum necessary permissions

## Resource Limits Per Store

- **Pods**: Max 4
- **CPU Requests**: 1 core total, max 2 cores
- **Memory Requests**: 2Gi total, max 3Gi
- **Storage**: 5Gi total

Default per container:
- **WordPress**: 256Mi RAM, 200m CPU (limits: 512Mi, 500m)
- **MariaDB**: 128Mi RAM, 100m CPU (limits: 512Mi, 500m)

## Troubleshooting

### Store stuck in "Provisioning"
```bash
kubectl describe store <name> -n platform
kubectl logs -n platform deployment/platform-controller
```

### WordPress not accessible
```bash
kubectl get ingress -n store-<id>
kubectl get pods -n store-<id>
kubectl logs -n store-<id> <wordpress-pod-name>
```

### Setup Job failed
```bash
kubectl logs -n store-<id> job/<store-id>-wordpress-setup
kubectl describe job -n store-<id>
```

### Database connection issues
```bash
kubectl logs -n store-<id> <wordpress-pod-name>
kubectl exec -n store-<id> <mariadb-pod-name> -- mysqladmin ping
```

## Next Steps

1. Implement Flask API in `backend/app.py`
2. Implement kopf controller in `controller/controller.py`
3. Implement React dashboard in `frontend/src/`
4. Build and push Docker images
5. Test end-to-end store creation flow
6. Configure production k3s cluster
7. Set up CI/CD pipeline
8. Add monitoring and alerting

## License

MIT

## Contributing

This is an internship assignment project. See `docs/system-design.md` for detailed architecture and design decisions.
