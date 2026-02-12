# Store Provisioning Platform - System Design

## Overview

The Store Provisioning Platform is a Kubernetes-native system for provisioning on-demand WooCommerce e-commerce stores. Each store runs as isolated resources in its own namespace, with complete lifecycle management through Kubernetes Custom Resource Definitions (CRDs) and a Python-based operator.

## Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           Users / Operators                              │
└────────────────────────────┬────────────────────────────────────────────┘
                             │
                 ┌───────────┴────────────┐
                 │                        │
        ┌────────▼────────┐      ┌────────▼────────┐
        │ React Dashboard │      │    kubectl      │
        │  (Frontend UI)  │      │   (CLI Tool)    │
        └────────┬────────┘      └────────┬────────┘
                 │                        │
                 │                        │
        ┌────────▼────────────────────────▼────────┐
        │         Flask API (Backend)              │
        │  - REST endpoints for store management   │
        │  - Kubernetes client integration         │
        └────────┬─────────────────────────────────┘
                 │
                 │ Creates/Updates Store CRDs
                 │
        ┌────────▼─────────────────────────────────┐
        │      Kubernetes API Server                │
        │  - Stores Store CRDs                      │
        │  - Validates resources                    │
        └────────┬─────────────────────────────────┘
                 │
                 │ Watches Store CRDs
                 │
        ┌────────▼─────────────────────────────────┐
        │  kopf Controller (Operator)               │
        │  - onCreate: Provisions store             │
        │  - onDelete: Cleans up resources          │
        │  - onTimer: Health checks                 │
        └────────┬─────────────────────────────────┘
                 │
                 │ Runs helm install/uninstall
                 │
        ┌────────▼─────────────────────────────────┐
        │        Helm (Package Manager)             │
        │  - Installs store-chart per store         │
        │  - Manages releases                       │
        └────────┬─────────────────────────────────┘
                 │
                 │ Creates Kubernetes resources
                 │
    ┌────────────┴─────────────┬─────────────┬─────────────┐
    │                          │             │             │
┌───▼──────────────┐  ┌────────▼──────┐  ┌──▼──────────┐  │
│ Store Namespace  │  │ Store         │  │ Store       │  │
│  store-shop1     │  │ Namespace     │  │ Namespace   │  │
│                  │  │ store-shop2   │  │ store-shop3 │  │
│ ┌──────────────┐ │  └───────────────┘  └─────────────┘  │
│ │  WordPress   │ │                                       │
│ │ + WooCommerce│ │                                       │
│ └──────────────┘ │                                       │
│ ┌──────────────┐ │                                       │
│ │   MariaDB    │ │                                       │
│ └──────────────┘ │                                       │
│ ┌──────────────┐ │                                       │
│ │   Ingress    │ │                                       │
│ └──────────────┘ │                                       │
│ ┌──────────────┐ │                                       │
│ │ NetworkPolicy│ │                                       │
│ └──────────────┘ │                                       │
└──────────────────┘                                       │
                                                           │
External Traffic ──────────────────────────────────────────┘
(via NGINX Ingress Controller)
```

## Component Responsibilities

### 1. React Dashboard (Frontend)

**Purpose**: Web UI for managing stores

**Responsibilities**:
- Display list of provisioned stores
- Show store status (Provisioning, Ready, Failed, etc.)
- Provide form for creating new stores
- Delete stores with confirmation
- Display store URLs and admin credentials
- Real-time status updates (polling or WebSocket)

**Technology Stack**:
- React 18
- Vite (build tool)
- Axios (HTTP client)
- Served via NGINX in production

**Key Features**:
- Store cards with status indicators
- Create store modal with validation
- Copy-to-clipboard for URLs
- Auto-refresh store list

### 2. Flask API (Backend)

**Purpose**: REST API for store management

**Responsibilities**:
- Create Store CRDs in Kubernetes
- List all stores with status
- Get detailed store information
- Delete Store CRDs
- Validate store creation requests
- Handle authentication (future)

**Endpoints**:
```
POST   /api/stores        - Create new store
GET    /api/stores        - List all stores
GET    /api/stores/:id    - Get store details
DELETE /api/stores/:id    - Delete store
GET    /health            - Health check
```

**Technology Stack**:
- Flask 3.0
- kubernetes-client library
- Flask-CORS for cross-origin requests

**Key Operations**:
1. **Create Store**:
   - Generate unique storeId from displayName
   - Create Store CRD in `platform` namespace
   - Return store details with initial status

2. **List Stores**:
   - Query all Store CRDs
   - Return array with status information

3. **Delete Store**:
   - Delete Store CRD
   - Controller handles cleanup asynchronously

### 3. kopf Controller (Operator)

**Purpose**: Kubernetes operator that reconciles Store CRDs

**Responsibilities**:
- Watch for Store CRD creation/deletion/updates
- Provision stores via Helm
- Update Store status throughout lifecycle
- Cleanup resources on deletion
- Periodic health checks
- Event logging

**Event Handlers**:

#### onCreate Handler
```python
@kopf.on.create('platform.urumi.io', 'v1', 'stores')
def create_store(spec, name, namespace, **kwargs):
    # 1. Extract store details from spec
    # 2. Update status to "Provisioning"
    # 3. Run helm install with store-chart
    # 4. Update status to "Installing"
    # 5. Monitor deployment progress
    # 6. Update status to "Ready" when complete
```

#### onDelete Handler
```python
@kopf.on.delete('platform.urumi.io', 'v1', 'stores')
def delete_store(spec, name, namespace, **kwargs):
    # 1. Update status to "Deleting"
    # 2. Run helm uninstall
    # 3. Delete namespace
    # 4. Log completion
```

#### onTimer Handler (Optional)
```python
@kopf.timer('platform.urumi.io', 'v1', 'stores', interval=30)
def check_store_health(spec, name, namespace, status, **kwargs):
    # 1. Check if pods are running
    # 2. Check if ingress is configured
    # 3. Check if WordPress is accessible
    # 4. Update status if changed
```

**Technology Stack**:
- kopf (Kubernetes Operator Framework)
- kubernetes-client library
- subprocess for helm/kubectl commands

**Status Phases**:
- **Provisioning**: Helm install initiated
- **Installing**: Pods being created
- **Configuring**: WordPress setup job running
- **Ready**: Store accessible and healthy
- **Failed**: Error during provisioning
- **Deleting**: Cleanup in progress

### 4. Store CRD (Custom Resource Definition)

**Purpose**: Kubernetes API extension for Store resources

**API Group**: `platform.urumi.io/v1`

**Schema**:
```yaml
apiVersion: platform.urumi.io/v1
kind: Store
metadata:
  name: my-store
  namespace: platform
spec:
  storeType: woocommerce      # or medusa
  displayName: "My Store"
  baseDomain: local.store      # Optional, defaults to local.store
status:
  phase: Ready
  url: http://my-store.local.store
  adminUrl: http://my-store.local.store/wp-admin
  message: "Store is ready"
  createdAt: "2024-01-15T10:30:00Z"
  readyAt: "2024-01-15T10:35:00Z"
  events:
    - timestamp: "2024-01-15T10:30:00Z"
      message: "Store provisioning started"
    - timestamp: "2024-01-15T10:35:00Z"
      message: "Store is ready"
```

**Printer Columns**:
```
NAME        TYPE          PHASE    URL                             AGE
my-store    woocommerce   Ready    http://my-store.local.store     5m
```

### 5. Store Chart (Helm Chart)

**Purpose**: Package individual store resources

**Resources Created Per Store**:

1. **Namespace**: `store-{storeId}`
   - Isolated namespace for all store resources

2. **MariaDB StatefulSet**:
   - Image: `mariadb:10.11`
   - Storage: 1Gi PVC
   - Credentials: Generated secrets with idempotency
   - Probes: `mysqladmin ping`
   - Resources: 128Mi/100m requests, 512Mi/500m limits

3. **WordPress Deployment**:
   - Image: `wordpress:6.4-php8.1-apache`
   - Database connection via secrets
   - WP-CRON disabled via `WORDPRESS_CONFIG_EXTRA`
   - Probes: HTTP GET / and TCP 80
   - Resources: 256Mi/200m requests, 512Mi/500m limits

4. **WordPress Setup Job**:
   - Image: `wordpress:cli-2.10-php8.1`
   - Waits for WordPress to be responsive
   - Installs WordPress core
   - Installs and activates WooCommerce
   - Creates sample products
   - Enables Cash on Delivery payment
   - Configures basic store settings
   - Idempotent: Can run multiple times safely
   - BackoffLimit: 3

5. **Ingress**:
   - Class: `nginx`
   - Host: `{storeId}.{baseDomain}`
   - Routes to WordPress service on port 80
   - Annotations for proxy settings

6. **NetworkPolicy**:
   - Default deny all traffic
   - Allow ingress from `ingress-nginx` namespace to WordPress:80
   - Allow WordPress to MariaDB:3306
   - Allow DNS egress to `kube-system`:53
   - Allow HTTP/HTTPS egress for plugin downloads

7. **ResourceQuota**:
   - Max 4 pods
   - Requests: 1 CPU, 2Gi memory, 5Gi storage
   - Limits: 2 CPU, 3Gi memory

8. **LimitRange**:
   - Default container: 256Mi memory, 200m CPU
   - Max container: 512Mi memory, 500m CPU

**Values Structure**:
```yaml
storeId: "my-store"              # Required
storeType: "woocommerce"
displayName: "My Store"
baseDomain: "local.store"

mariadb:
  storage: { size: 1Gi }
  resources: { ... }

wordpress:
  replicaCount: 1
  resources: { ... }

ingress:
  enabled: true
  className: "nginx"

networkPolicy:
  enabled: true

resourceQuota:
  enabled: true

limitRange:
  enabled: true
```

### 6. Platform Chart (Helm Chart)

**Purpose**: Deploy platform components

**Resources Created**:

1. **Platform Namespace**: `platform`

2. **Store CRD**: Registered at cluster level

3. **Controller RBAC**:
   - ServiceAccount: `store-controller`
   - ClusterRole with permissions for:
     - Store CRDs (full access)
     - Namespaces, Deployments, StatefulSets, Services, Ingresses
     - Secrets, ConfigMaps, PVCs
     - Jobs, ResourceQuotas, LimitRanges, NetworkPolicies
     - Events (for status updates)
   - ClusterRoleBinding

4. **Controller Deployment**:
   - Runs kopf operator
   - Uses ServiceAccount for RBAC
   - Mounts store-chart (or references it)

5. **API Deployment**:
   - Flask backend
   - Service on port 5000
   - Health checks on `/health`

6. **Dashboard Deployment**:
   - React frontend served by NGINX
   - Service on port 80

7. **Platform Ingress**:
   - Routes `api.{baseDomain}` to API service
   - Routes `dashboard.{baseDomain}` to Dashboard service

## Data Flows

### Store Creation Flow

```
1. User → Dashboard: Submits create store form
   ↓
2. Dashboard → API: POST /api/stores
   {
     "displayName": "Demo Store",
     "storeType": "woocommerce"
   }
   ↓
3. API → Kubernetes: Creates Store CRD
   apiVersion: platform.urumi.io/v1
   kind: Store
   metadata:
     name: demo-store
     namespace: platform
   spec:
     storeType: woocommerce
     displayName: "Demo Store"
     baseDomain: local.store
   ↓
4. API → Dashboard: Returns store details
   ↓
5. Controller: Detects Store CRD creation (@kopf.on.create)
   ↓
6. Controller → Store CRD: Updates status to "Provisioning"
   ↓
7. Controller → Helm: Runs helm install
   helm install demo-store ./store-chart \
     --namespace store-demo-store \
     --create-namespace \
     --set storeId=demo-store \
     --set storeType=woocommerce \
     --set baseDomain=local.store \
     --set displayName="Demo Store"
   ↓
8. Helm → Kubernetes: Creates resources
   - Namespace: store-demo-store
   - MariaDB Secret (with generated passwords)
   - WordPress Secret (with generated admin password)
   - MariaDB PVC
   - MariaDB StatefulSet
   - MariaDB Service
   - WordPress Deployment
   - WordPress Service
   - WordPress Setup Job
   - Ingress
   - NetworkPolicy
   - ResourceQuota
   - LimitRange
   ↓
9. Kubernetes: Schedules pods
   - MariaDB pod starts, initializes database
   - WordPress pod starts, connects to MariaDB
   ↓
10. WordPress Setup Job: Runs WP-CLI commands
    - Waits for WordPress to respond
    - Installs WordPress core
    - Installs WooCommerce plugin
    - Creates sample products
    - Enables payment gateways
    - Job completes successfully
    ↓
11. Controller: Monitors progress
    - Checks pod status
    - Updates Store status to "Installing" → "Configuring" → "Ready"
    - Sets status.url and status.adminUrl
    - Adds events to status.events
    ↓
12. Dashboard: Polls API, displays updated status
    ↓
13. User: Accesses store at http://demo-store.local.store
```

### Store Deletion Flow

```
1. User → Dashboard: Clicks delete on store card
   ↓
2. Dashboard → User: Shows confirmation dialog
   ↓
3. User: Confirms deletion
   ↓
4. Dashboard → API: DELETE /api/stores/demo-store
   ↓
5. API → Kubernetes: Deletes Store CRD
   kubectl delete store demo-store -n platform
   ↓
6. Controller: Detects Store CRD deletion (@kopf.on.delete)
   ↓
7. Controller → Store CRD: Updates status to "Deleting"
   ↓
8. Controller → Helm: Runs helm uninstall
   helm uninstall demo-store --namespace store-demo-store
   ↓
9. Helm → Kubernetes: Deletes resources
   - WordPress Deployment → Pods terminated
   - MariaDB StatefulSet → Pod terminated
   - Services deleted
   - Ingress deleted
   - Setup Job deleted (if still present)
   - Secrets deleted
   - PVC deleted (data loss!)
   ↓
10. Controller → Kubernetes: Deletes namespace
    kubectl delete namespace store-demo-store
    ↓
11. Kubernetes: Garbage collects remaining resources
    - NetworkPolicy
    - ResourceQuota
    - LimitRange
    ↓
12. Controller: Logs cleanup completion
    ↓
13. Dashboard: Store disappears from list
```

## Security Model

### Network Isolation

**NetworkPolicy Enforcement**:
- Default deny all ingress and egress
- Explicit allow rules for necessary traffic only

**Allowed Traffic**:
1. **Ingress to WordPress**:
   - From: `ingress-nginx` namespace
   - To: WordPress pods on port 80
   - Purpose: External HTTP access

2. **WordPress to MariaDB**:
   - From: WordPress pods
   - To: MariaDB pods on port 3306
   - Purpose: Database queries

3. **DNS Resolution**:
   - From: All pods
   - To: `kube-system` namespace on UDP 53
   - Purpose: Service discovery

4. **HTTP/HTTPS Egress**:
   - From: WordPress pods
   - To: Any destination on ports 80, 443
   - Purpose: Plugin downloads, API calls

**Blocked Traffic**:
- External access to MariaDB (no direct database connections)
- Cross-store traffic (store-shop1 cannot reach store-shop2)
- Direct pod-to-pod communication without service

### Resource Limits

**Per-Store ResourceQuota**:
```yaml
hard:
  pods: "4"                    # Max 4 pods per store
  requests.cpu: "1"            # 1 CPU core total
  requests.memory: "2Gi"       # 2Gi RAM total
  limits.cpu: "2"              # 2 CPU cores max
  limits.memory: "3Gi"         # 3Gi RAM max
  requests.storage: "5Gi"      # 5Gi storage total
```

**Per-Container LimitRange**:
```yaml
limits:
  - type: Container
    default:
      memory: "512Mi"          # Default limit
      cpu: "500m"
    defaultRequest:
      memory: "256Mi"          # Default request
      cpu: "200m"
    max:
      memory: "512Mi"          # Maximum allowed
      cpu: "500m"
```

**Prevents**:
- Resource exhaustion attacks
- Runaway containers consuming all cluster resources
- "Noisy neighbor" problems between stores

### Secrets Management

**Password Generation**:
- MariaDB root password: 16-character random alphanumeric
- MariaDB user password: 16-character random alphanumeric
- WordPress admin password: 16-character random alphanumeric
- Generated using Helm's `randAlphaNum` function

**Idempotency**:
- Helm `lookup` function checks if secret exists
- Preserves existing passwords on upgrades
- Only generates new passwords on initial install

**Access Control**:
- Secrets stored in store namespace
- Only pods in same namespace can access
- Mounted as environment variables or volumes

### RBAC

**Controller Permissions**:
- ClusterRole with minimum necessary permissions
- Full access to Store CRDs
- Full access to namespaces, deployments, services, etc.
- No access to cluster-level resources beyond what's needed

**User Permissions** (Future):
- Role-based access to API endpoints
- Multi-tenancy: users can only see their own stores
- Admin users can see all stores

## Failure Modes and Recovery

### Pod Failures

**MariaDB Pod Failure**:
- Kubernetes restarts pod automatically
- StatefulSet ensures stable identity
- PVC preserves data across restarts
- WordPress may experience connection errors until MariaDB is ready
- Impact: Store temporarily unavailable (1-2 minutes)

**WordPress Pod Failure**:
- Kubernetes restarts pod automatically
- Deployment ensures desired replicas
- emptyDir volume loses data (acceptable, WordPress files are in image)
- Impact: Store temporarily unavailable (30 seconds)

**Recovery**:
- Automatic via Kubernetes liveness probes
- No manual intervention needed
- Store returns to "Ready" status once pods are healthy

### Setup Job Failure

**Causes**:
- WordPress not ready in time
- WooCommerce plugin download failure
- Network issues
- Database connection failure

**Recovery**:
- Job has `backoffLimit: 3` (retries 3 times)
- Each retry includes wait loop for WordPress
- If all retries fail, Job status is "Failed"
- Controller can detect and update Store status to "Failed"
- Manual intervention: Delete and recreate job, or delete store

### Helm Install Failure

**Causes**:
- Invalid values
- Namespace already exists
- Resource quota exceeded
- Image pull failures

**Recovery**:
- Controller catches subprocess error
- Updates Store status to "Failed" with error message
- User can view error in Store status
- User can delete Store to clean up
- Fix issue and create new store

### Controller Crash

**Impact**:
- Store CRD events are not processed
- Existing stores continue to run (Kubernetes maintains state)
- New stores are not provisioned
- Deletions are not cleaned up

**Recovery**:
- Kubernetes restarts controller pod
- kopf resumes watching from last checkpoint
- Pending events are processed
- No data loss

### API Crash

**Impact**:
- Dashboard cannot create/delete stores
- Existing stores continue to run
- User can still use `kubectl` to manage Store CRDs directly

**Recovery**:
- Kubernetes restarts API pod
- Service routes traffic to new pod
- Dashboard reconnects automatically

### Network Partition

**Scenario**: Control plane separated from worker nodes

**Impact**:
- Existing stores continue to run on worker nodes
- Controller cannot update Store status
- New stores cannot be created

**Recovery**:
- Kubernetes handles network healing
- Once connectivity restored, controller resumes operations
- Status updates catch up

## Scalability

### Current Limits

**Per-Store Resources**:
- 4 pods max (ResourceQuota)
- 2 CPU cores max (ResourceQuota)
- 3Gi RAM max (ResourceQuota)
- 5Gi storage max (ResourceQuota)

**Cluster Capacity** (Example on Kind):
- Assume 4 CPU cores, 8Gi RAM available
- Max ~4 stores before resource exhaustion
- Production k3s cluster: Scale based on available resources

### Scaling Strategies

**Horizontal Scaling (More Stores)**:
1. Add more worker nodes to cluster
2. Each store is lightweight (2 pods: WordPress + MariaDB)
3. Namespace isolation prevents interference
4. NetworkPolicy limits cross-store traffic

**Vertical Scaling (Larger Stores)**:
1. Adjust ResourceQuota per store
2. Increase WordPress/MariaDB resource limits
3. Add persistent storage for WordPress files (currently emptyDir)

**Controller Scaling**:
- Currently single replica (avoid race conditions)
- kopf handles events sequentially
- Future: Leader election for HA

**API Scaling**:
- Stateless, can scale horizontally
- Add more replicas in Deployment
- Load balancing via Service

## Observability

### Logging

**Controller Logs**:
```bash
kubectl logs -n platform deployment/platform-controller -f
```
- Store creation events
- Helm command output
- Error messages
- Status updates

**API Logs**:
```bash
kubectl logs -n platform deployment/platform-api -f
```
- HTTP requests
- Store CRD operations
- Error responses

**Store Logs**:
```bash
# WordPress logs
kubectl logs -n store-{id} deployment/{id}-wordpress -f

# MariaDB logs
kubectl logs -n store-{id} statefulset/{id}-mariadb -f

# Setup Job logs
kubectl logs -n store-{id} job/{id}-wordpress-setup
```

### Metrics (Future)

- Prometheus metrics for controller
- API response times
- Store provisioning duration
- Resource utilization per store
- Active stores count

### Events

**Kubernetes Events**:
```bash
kubectl get events -n store-{id} --sort-by='.lastTimestamp'
```
- Pod scheduling
- Image pulls
- Container starts/restarts
- Probe failures

**Store CRD Events**:
```bash
kubectl describe store {name} -n platform
```
- Status transitions
- Error messages
- Provisioning milestones

## Deployment Environments

### Local Development (Kind)

**Setup**:
```bash
./setup-cluster.sh
helm install platform ./platform-chart -f ./platform-chart/values-local.yaml
```

**Configuration**:
- Base domain: `local.store`
- Image pull policy: `Never` (use local images)
- No TLS
- `/etc/hosts` entries for ingress

**Use Cases**:
- Development and testing
- Chart validation
- Controller development

### Production (k3s)

**Setup**:
```bash
# Install k3s on VPS
curl -sfL https://get.k3s.io | sh -

# Install platform
helm install platform ./platform-chart -f ./platform-chart/values-prod.yaml
```

**Configuration**:
- Base domain: Production domain (e.g., `yourdomain.com`)
- Image pull policy: `IfNotPresent`
- TLS enabled via cert-manager
- External DNS for wildcard subdomains
- Multiple API/Dashboard replicas for HA

**Infrastructure**:
- VPS with k3s (single-node or multi-node)
- Persistent storage provider
- External ingress (LoadBalancer or NodePort)
- DNS configuration for wildcard `*.yourdomain.com`

## Future Enhancements

### Short-Term

1. **Medusa Support**: Add second store engine
2. **Persistent WordPress Files**: Use PVC instead of emptyDir
3. **Store Updates**: Allow updating store settings via CRD
4. **Backup/Restore**: Scheduled database backups
5. **Metrics Dashboard**: Grafana dashboards for observability

### Long-Term

1. **Multi-Tenancy**: Users can only see their own stores
2. **Custom Domains**: Allow users to bring their own domains
3. **Auto-Scaling**: Scale WordPress replicas based on traffic
4. **CDN Integration**: CloudFlare or similar for static assets
5. **Database Clustering**: Multi-replica MariaDB for HA
6. **GitOps**: Integrate with ArgoCD for declarative deployments
7. **Cost Tracking**: Track resource costs per store
8. **Store Templates**: Pre-configured store types (fashion, food, etc.)

## Technology Choices

### Why Helm?

- **Templating**: Parameterize resources per store
- **Packaging**: Bundle all store resources together
- **Lifecycle**: Install, upgrade, uninstall operations
- **Idempotency**: Lookup function for secrets
- **Widespread Adoption**: Industry standard

### Why kopf?

- **Pythonic**: Easy to write operators in Python
- **Event-Driven**: Decorators for create/update/delete
- **Status Management**: Built-in status updates
- **Retry Logic**: Automatic retries on failures
- **Timers**: Periodic reconciliation

### Why Flask?

- **Lightweight**: Simple REST API needs
- **Python Ecosystem**: Integrates with kubernetes-client
- **Fast Development**: Quick to prototype
- **Flexible**: Easy to add authentication, validation

### Why React?

- **Component-Based**: Reusable UI components
- **Modern**: Industry standard for SPAs
- **Ecosystem**: Rich library ecosystem
- **Fast**: Vite for instant HMR

## Conclusion

The Store Provisioning Platform demonstrates a production-ready Kubernetes-native architecture for multi-tenant SaaS applications. Key strengths:

1. **Isolation**: Each store in its own namespace with NetworkPolicy
2. **Security**: RBAC, secrets, resource quotas
3. **Observability**: Comprehensive logging and status tracking
4. **Scalability**: Horizontal scaling via namespace-per-tenant pattern
5. **Reliability**: Automatic pod restarts, idempotent operations
6. **Maintainability**: Helm charts for consistency, kopf for operator logic

The system is ready for local development and can be deployed to production k3s clusters with minimal configuration changes.
