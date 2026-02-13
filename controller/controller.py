"""
Store Provisioning Platform - Kubernetes Controller
kopf-based operator that watches Store CRDs and provisions WooCommerce stores via Helm
"""

import asyncio
import kopf
import logging
import os
import re
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Tuple

from kubernetes_asyncio import client, config
from kubernetes_asyncio.client.rest import ApiException

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration from environment variables
STORE_CHART_PATH = os.getenv('STORE_CHART_PATH', '/charts/store-chart')
BASE_DOMAIN = os.getenv('BASE_DOMAIN', 'local.store')
PLATFORM_NAMESPACE = os.getenv('PLATFORM_NAMESPACE', 'platform')

# Timeouts (in seconds)
HELM_INSTALL_TIMEOUT = 300
HELM_UNINSTALL_TIMEOUT = 120
DEPLOYMENT_READY_TIMEOUT = 600
JOB_COMPLETION_TIMEOUT = 300
POLL_INTERVAL = 10


# ============================================================================
# Helper Functions
# ============================================================================

def sanitize_store_id(name: str) -> str:
    """
    Sanitize store name for Kubernetes naming conventions.
    - Lowercase
    - Replace underscores with hyphens
    - Remove non-alphanumeric characters (except hyphens)
    - Ensure starts and ends with alphanumeric
    - Max 20 characters
    """
    # Convert to lowercase
    sanitized = name.lower()

    # Replace underscores with hyphens
    sanitized = sanitized.replace('_', '-')

    # Remove non-alphanumeric characters except hyphens
    sanitized = re.sub(r'[^a-z0-9-]', '', sanitized)

    # Remove leading/trailing hyphens
    sanitized = sanitized.strip('-')

    # Ensure starts with alphanumeric
    sanitized = re.sub(r'^[^a-z0-9]+', '', sanitized)

    # Truncate to 20 characters
    sanitized = sanitized[:20]

    # Remove trailing hyphens after truncation
    sanitized = sanitized.rstrip('-')

    # If empty, generate a default
    if not sanitized:
        sanitized = 'store'

    return sanitized


def get_timestamp() -> str:
    """Get current timestamp in ISO 8601 format"""
    return datetime.now(timezone.utc).isoformat()


async def run_command(cmd: list, timeout: int = 60) -> Tuple[int, str, str]:
    """
    Run a command asynchronously using asyncio subprocess.

    Returns:
        tuple: (returncode, stdout, stderr)
    """
    try:
        logger.info(f"Running command: {' '.join(cmd)}")

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            logger.error(f"Command timed out after {timeout}s: {' '.join(cmd)}")
            process.kill()
            await process.wait()
            return -1, "", f"Command timed out after {timeout}s"

        stdout_str = stdout.decode('utf-8') if stdout else ""
        stderr_str = stderr.decode('utf-8') if stderr else ""

        logger.info(f"Command exit code: {process.returncode}")
        if stdout_str:
            logger.debug(f"Command stdout: {stdout_str}")
        if stderr_str:
            logger.debug(f"Command stderr: {stderr_str}")

        return process.returncode, stdout_str, stderr_str

    except Exception as e:
        logger.error(f"Error running command: {e}")
        return -1, "", str(e)


async def check_helm_release_exists(release_name: str, namespace: str) -> bool:
    """
    Check if a Helm release already exists.

    Returns:
        bool: True if release exists, False otherwise
    """
    try:
        cmd = [
            'helm', 'list',
            '-n', namespace,
            '--filter', release_name,
            '-q'
        ]

        returncode, stdout, stderr = await run_command(cmd, timeout=30)

        if returncode == 0 and stdout.strip() == release_name:
            logger.info(f"Helm release '{release_name}' already exists in namespace '{namespace}'")
            return True

        return False

    except Exception as e:
        logger.warning(f"Error checking helm release: {e}")
        return False


async def helm_install(
    release_name: str,
    chart_path: str,
    namespace: str,
    values: Dict[str, str]
) -> Tuple[bool, str]:
    """
    Install a Helm chart.

    Returns:
        tuple: (success, error_message)
    """
    try:
        # Build helm install command
        cmd = [
            'helm', 'install',
            release_name,
            chart_path,
            '--namespace', namespace,
            '--wait',
            '--timeout', f'{HELM_INSTALL_TIMEOUT}s'
        ]

        # Add values
        for key, value in values.items():
            cmd.extend(['--set', f'{key}={value}'])

        returncode, stdout, stderr = await run_command(cmd, timeout=HELM_INSTALL_TIMEOUT + 10)

        if returncode == 0:
            logger.info(f"Helm install successful: {release_name}")
            return True, ""
        else:
            error_msg = f"Helm install failed: {stderr or stdout}"
            logger.error(error_msg)
            return False, error_msg

    except Exception as e:
        error_msg = f"Exception during helm install: {str(e)}"
        logger.error(error_msg)
        return False, error_msg


async def helm_uninstall(release_name: str, namespace: str) -> Tuple[bool, str]:
    """
    Uninstall a Helm release.

    Returns:
        tuple: (success, error_message)
    """
    try:
        cmd = [
            'helm', 'uninstall',
            release_name,
            '--namespace', namespace,
            '--wait',
            '--timeout', f'{HELM_UNINSTALL_TIMEOUT}s'
        ]

        returncode, stdout, stderr = await run_command(cmd, timeout=HELM_UNINSTALL_TIMEOUT + 10)

        if returncode == 0:
            logger.info(f"Helm uninstall successful: {release_name}")
            return True, ""
        else:
            # Non-zero return code, but might be OK if release doesn't exist
            if "not found" in stderr.lower() or "not found" in stdout.lower():
                logger.warning(f"Helm release not found (already deleted?): {release_name}")
                return True, ""

            error_msg = f"Helm uninstall failed: {stderr or stdout}"
            logger.error(error_msg)
            return False, error_msg

    except Exception as e:
        error_msg = f"Exception during helm uninstall: {str(e)}"
        logger.error(error_msg)
        return False, error_msg


async def check_deployment_ready(deployment_name: str, namespace: str) -> bool:
    """
    Check if a Deployment has available replicas.

    Returns:
        bool: True if deployment is ready, False otherwise
    """
    try:
        async with client.ApiClient() as api_client:
            apps_v1 = client.AppsV1Api(api_client)

            deployment = await apps_v1.read_namespaced_deployment(
                name=deployment_name,
                namespace=namespace
            )

            if deployment.status.available_replicas and deployment.status.available_replicas > 0:
                logger.info(f"Deployment '{deployment_name}' is ready with {deployment.status.available_replicas} replicas")
                return True

            logger.debug(f"Deployment '{deployment_name}' not ready yet. Available: {deployment.status.available_replicas}")
            return False

    except ApiException as e:
        if e.status == 404:
            logger.debug(f"Deployment '{deployment_name}' not found yet in namespace '{namespace}'")
        else:
            logger.warning(f"Error checking deployment: {e}")
        return False
    except Exception as e:
        logger.warning(f"Exception checking deployment: {e}")
        return False


async def check_job_completed(job_name: str, namespace: str) -> Tuple[bool, bool]:
    """
    Check if a Job has completed successfully.

    Returns:
        tuple: (exists, succeeded)
            - exists: True if job exists, False otherwise
            - succeeded: True if job completed successfully, False if failed or still running
    """
    try:
        async with client.ApiClient() as api_client:
            batch_v1 = client.BatchV1Api(api_client)

            job = await batch_v1.read_namespaced_job(
                name=job_name,
                namespace=namespace
            )

            if job.status.succeeded and job.status.succeeded > 0:
                logger.info(f"Job '{job_name}' completed successfully")
                return True, True

            if job.status.failed and job.status.failed > 0:
                logger.warning(f"Job '{job_name}' failed")
                return True, False

            logger.debug(f"Job '{job_name}' still running")
            return True, False

    except ApiException as e:
        if e.status == 404:
            logger.debug(f"Job '{job_name}' not found yet in namespace '{namespace}'")
            return False, False
        else:
            logger.warning(f"Error checking job: {e}")
            return False, False
    except Exception as e:
        logger.warning(f"Exception checking job: {e}")
        return False, False


async def poll_for_deployment_ready(deployment_name: str, namespace: str, timeout: int) -> bool:
    """
    Poll for deployment readiness with timeout.

    Returns:
        bool: True if deployment became ready, False if timeout
    """
    logger.info(f"Polling for deployment '{deployment_name}' in namespace '{namespace}'")

    start_time = asyncio.get_event_loop().time()

    while True:
        if await check_deployment_ready(deployment_name, namespace):
            return True

        elapsed = asyncio.get_event_loop().time() - start_time
        if elapsed >= timeout:
            logger.error(f"Timeout waiting for deployment '{deployment_name}' to be ready")
            return False

        await asyncio.sleep(POLL_INTERVAL)


async def poll_for_job_completion(job_name: str, namespace: str, timeout: int) -> bool:
    """
    Poll for job completion with timeout.

    Returns:
        bool: True if job completed successfully, False if failed or timeout
    """
    logger.info(f"Polling for job '{job_name}' in namespace '{namespace}'")

    start_time = asyncio.get_event_loop().time()

    while True:
        exists, succeeded = await check_job_completed(job_name, namespace)

        if exists and succeeded:
            return True

        if exists and not succeeded:
            # Job exists but failed
            logger.error(f"Job '{job_name}' failed")
            return False

        elapsed = asyncio.get_event_loop().time() - start_time
        if elapsed >= timeout:
            logger.error(f"Timeout waiting for job '{job_name}' to complete")
            return False

        await asyncio.sleep(POLL_INTERVAL)


async def create_namespace(namespace: str, release_name: str) -> bool:
    """
    Create a namespace with Helm-compatible labels/annotations if it doesn't exist.
    Returns True if created or already exists, False on error.
    """
    try:
        async with client.ApiClient() as api_client:
            core_v1 = client.CoreV1Api(api_client)

            # Check if namespace exists
            try:
                await core_v1.read_namespace(name=namespace)
                logger.info(f"Namespace '{namespace}' already exists")
                return True
            except ApiException as e:
                if e.status != 404:
                    raise

            # Create namespace with Helm-compatible metadata
            ns_body = client.V1Namespace(
                metadata=client.V1ObjectMeta(
                    name=namespace,
                    labels={
                        'platform.urumi.io/managed': 'true',
                        'name': namespace,
                        'app.kubernetes.io/managed-by': 'Helm'
                    },
                    annotations={
                        'meta.helm.sh/release-name': release_name,
                        'meta.helm.sh/release-namespace': namespace
                    }
                )
            )
            await core_v1.create_namespace(body=ns_body)
            logger.info(f"Namespace '{namespace}' created with Helm metadata")
            return True
    except Exception as e:
        logger.error(f"Error creating namespace: {e}")
        return False


async def delete_namespace(namespace: str) -> bool:
    """
    Delete a Kubernetes namespace.

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        async with client.ApiClient() as api_client:
            core_v1 = client.CoreV1Api(api_client)

            await core_v1.delete_namespace(name=namespace)
            logger.info(f"Namespace '{namespace}' deletion initiated")
            return True

    except ApiException as e:
        if e.status == 404:
            logger.warning(f"Namespace '{namespace}' not found (already deleted?)")
            return True
        else:
            logger.error(f"Error deleting namespace: {e}")
            return False
    except Exception as e:
        logger.error(f"Exception deleting namespace: {e}")
        return False


def build_status_update(
    phase: str,
    url: Optional[str] = None,
    admin_url: Optional[str] = None,
    message: Optional[str] = None,
    created_at: Optional[str] = None,
    ready_at: Optional[str] = None
) -> Dict[str, Any]:
    """
    Build a status update dictionary.
    """
    status = {'phase': phase}

    if url:
        status['url'] = url
    if admin_url:
        status['adminUrl'] = admin_url
    if message:
        status['message'] = message
    if created_at:
        status['createdAt'] = created_at
    if ready_at:
        status['readyAt'] = ready_at

    return status


# ============================================================================
# Kopf Handlers
# ============================================================================

@kopf.on.startup()
async def startup_handler(settings: kopf.OperatorSettings, **kwargs):
    """
    Startup handler to verify prerequisites.
    """
    logger.info("=" * 70)
    logger.info("Store Provisioning Controller Starting")
    logger.info("=" * 70)
    logger.info(f"Store Chart Path: {STORE_CHART_PATH}")
    logger.info(f"Base Domain: {BASE_DOMAIN}")
    logger.info(f"Platform Namespace: {PLATFORM_NAMESPACE}")

    # Check if helm is available
    try:
        returncode, stdout, stderr = await run_command(['helm', 'version', '--short'], timeout=10)
        if returncode == 0:
            logger.info(f"Helm version: {stdout.strip()}")
        else:
            logger.error("Helm is not available!")
            raise Exception("Helm not found")
    except Exception as e:
        logger.error(f"Failed to verify Helm: {e}")
        raise

    # Check if store chart exists
    if not os.path.exists(STORE_CHART_PATH):
        logger.error(f"Store chart path does not exist: {STORE_CHART_PATH}")
        raise Exception(f"Store chart not found at {STORE_CHART_PATH}")

    logger.info(f"Store chart found at: {STORE_CHART_PATH}")

    # Load kubernetes config
    try:
        config.load_incluster_config()
        logger.info("Loaded in-cluster Kubernetes config")
    except Exception as e:
        logger.warning(f"Failed to load in-cluster config: {e}")
        try:
            await config.load_kube_config()
            logger.info("Loaded kubeconfig from file")
        except Exception as e2:
            logger.error(f"Failed to load kubeconfig: {e2}")
            raise

    # Configure kopf settings
    settings.watching.server_timeout = 600
    settings.watching.client_timeout = 660

    logger.info("Startup checks completed successfully")
    logger.info("=" * 70)


@kopf.on.create('platform.urumi.io', 'v1', 'stores')
async def create_store(spec, name, namespace, patch, logger, **kwargs):
    """
    Handle Store CRD creation - provision a new WooCommerce store.
    """
    logger.info(f"Creating store: {name} in namespace: {namespace}")
    logger.info(f"Store spec: {spec}")

    # Extract spec fields
    store_type = spec.get('storeType', 'woocommerce')
    display_name = spec.get('displayName', name)
    base_domain = spec.get('baseDomain', BASE_DOMAIN)

    # Generate sanitized store ID
    store_id = sanitize_store_id(name)
    logger.info(f"Sanitized store ID: {store_id}")

    # Store namespace and release name
    store_namespace = f"store-{store_id}"
    release_name = f"store-{store_id}"

    created_at = get_timestamp()

    try:
        # ========================================
        # Phase 1: Provisioning
        # ========================================
        logger.info(f"[{name}] Phase: Provisioning")
        kopf.info(
            spec,
            reason='Provisioning',
            message=f'Starting provisioning of store {store_id}'
        )

        patch['status'] = build_status_update(
            phase='Provisioning',
            message=f'Starting provisioning of store {store_id}',
            created_at=created_at
        )

        # Check if release already exists (idempotency)
        release_exists = await check_helm_release_exists(release_name, store_namespace)

        if not release_exists:
            # Create namespace first
            logger.info(f"[{name}] Creating namespace: {store_namespace}")
            ns_created = await create_namespace(store_namespace, release_name)
            if not ns_created:
                error_msg = f"Failed to create namespace {store_namespace}"
                logger.error(f"[{name}] {error_msg}")
                kopf.exception(
                    spec,
                    reason='NamespaceCreationFailed',
                    message=error_msg
                )
                patch['status'] = build_status_update(
                    phase='Failed',
                    message=error_msg,
                    created_at=created_at
                )
                return

            # Run helm install
            logger.info(f"[{name}] Installing Helm chart")

            helm_values = {
                'storeId': store_id,
                'storeType': store_type,
                'displayName': display_name,
                'baseDomain': base_domain
            }

            success, error_msg = await helm_install(
                release_name=release_name,
                chart_path=STORE_CHART_PATH,
                namespace=store_namespace,
                values=helm_values
            )

            if not success:
                logger.error(f"[{name}] Helm install failed: {error_msg}")
                kopf.exception(
                    spec,
                    reason='ProvisioningFailed',
                    message=f'Helm install failed: {error_msg}'
                )

                patch['status'] = build_status_update(
                    phase='Failed',
                    message=f'Helm install failed: {error_msg}',
                    created_at=created_at
                )
                return
        else:
            logger.info(f"[{name}] Helm release already exists, skipping install")

        # ========================================
        # Phase 2: Installing
        # ========================================
        logger.info(f"[{name}] Phase: Installing")
        kopf.info(
            spec,
            reason='Installing',
            message='Helm chart installed, waiting for pods'
        )

        patch['status'] = build_status_update(
            phase='Installing',
            message='Helm chart installed, waiting for pods',
            created_at=created_at
        )

        # Poll for WordPress deployment readiness
        wordpress_deployment = f"{release_name}-wordpress"
        logger.info(f"[{name}] Waiting for WordPress deployment: {wordpress_deployment}")

        deployment_ready = await poll_for_deployment_ready(
            deployment_name=wordpress_deployment,
            namespace=store_namespace,
            timeout=DEPLOYMENT_READY_TIMEOUT
        )

        if not deployment_ready:
            error_msg = f"WordPress deployment did not become ready within {DEPLOYMENT_READY_TIMEOUT}s"
            logger.error(f"[{name}] {error_msg}")
            kopf.exception(
                spec,
                reason='DeploymentTimeout',
                message=error_msg
            )

            patch['status'] = build_status_update(
                phase='Failed',
                message=error_msg,
                created_at=created_at
            )
            return

        # ========================================
        # Phase 3: Configuring
        # ========================================
        logger.info(f"[{name}] Phase: Configuring")
        kopf.info(
            spec,
            reason='Configuring',
            message='WordPress is running, waiting for setup job'
        )

        patch['status'] = build_status_update(
            phase='Configuring',
            message='WordPress is running, waiting for setup job',
            created_at=created_at
        )

        # Poll for WordPress setup job completion
        setup_job_name = f"{release_name}-wordpress-setup"
        logger.info(f"[{name}] Waiting for setup job: {setup_job_name}")

        job_completed = await poll_for_job_completion(
            job_name=setup_job_name,
            namespace=store_namespace,
            timeout=JOB_COMPLETION_TIMEOUT
        )

        if not job_completed:
            error_msg = f"WordPress setup job did not complete successfully within {JOB_COMPLETION_TIMEOUT}s"
            logger.error(f"[{name}] {error_msg}")
            kopf.exception(
                spec,
                reason='SetupJobFailed',
                message=error_msg
            )

            patch['status'] = build_status_update(
                phase='Failed',
                message=error_msg,
                created_at=created_at
            )
            return

        # ========================================
        # Phase 4: Ready
        # ========================================
        logger.info(f"[{name}] Phase: Ready")

        store_url = f"http://{store_id}.{base_domain}"
        admin_url = f"http://{store_id}.{base_domain}/wp-admin"
        ready_at = get_timestamp()

        kopf.info(
            spec,
            reason='Ready',
            message=f'Store is ready at {store_url}'
        )

        patch['status'] = build_status_update(
            phase='Ready',
            url=store_url,
            admin_url=admin_url,
            message='Store is ready and accessible',
            created_at=created_at,
            ready_at=ready_at
        )

        logger.info(f"[{name}] Store provisioned successfully!")
        logger.info(f"[{name}] Store URL: {store_url}")
        logger.info(f"[{name}] Admin URL: {admin_url}")

    except Exception as e:
        error_msg = f"Unexpected error during store creation: {str(e)}"
        logger.error(f"[{name}] {error_msg}")
        logger.exception(e)

        kopf.exception(
            spec,
            reason='UnexpectedError',
            message=error_msg
        )

        patch['status'] = build_status_update(
            phase='Failed',
            message=error_msg,
            created_at=created_at
        )


@kopf.on.delete('platform.urumi.io', 'v1', 'stores')
async def delete_store(spec, name, namespace, status, logger, **kwargs):
    """
    Handle Store CRD deletion - clean up store resources.
    """
    logger.info(f"Deleting store: {name} in namespace: {namespace}")

    # Generate store ID (same as during creation)
    store_id = sanitize_store_id(name)
    store_namespace = f"store-{store_id}"
    release_name = f"store-{store_id}"

    try:
        # Update status to Deleting (if we can still patch)
        logger.info(f"[{name}] Phase: Deleting")
        kopf.info(
            spec,
            reason='Deleting',
            message=f'Deleting store {store_id}'
        )

        # Uninstall Helm release
        logger.info(f"[{name}] Uninstalling Helm release: {release_name}")
        success, error_msg = await helm_uninstall(release_name, store_namespace)

        if not success:
            logger.warning(f"[{name}] Helm uninstall had issues: {error_msg}")
            # Continue with namespace deletion anyway

        # Delete namespace
        logger.info(f"[{name}] Deleting namespace: {store_namespace}")
        await delete_namespace(store_namespace)

        logger.info(f"[{name}] Store deletion completed")
        kopf.info(
            spec,
            reason='Deleted',
            message=f'Store {store_id} has been deleted'
        )

    except Exception as e:
        error_msg = f"Error during store deletion: {str(e)}"
        logger.error(f"[{name}] {error_msg}")
        logger.exception(e)

        kopf.exception(
            spec,
            reason='DeletionError',
            message=error_msg
        )


@kopf.on.resume('platform.urumi.io', 'v1', 'stores')
async def resume_store(spec, name, namespace, status, patch, logger, **kwargs):
    """
    Handle controller restart - reconcile partial states.
    """
    logger.info(f"Resuming store: {name} in namespace: {namespace}")
    logger.info(f"Current status: {status}")

    if not status:
        logger.info(f"[{name}] No status yet, skipping resume")
        return

    current_phase = status.get('phase')

    # If store is in transitional state, reconcile
    if current_phase in ['Provisioning', 'Installing', 'Configuring']:
        logger.info(f"[{name}] Store is in transitional phase '{current_phase}', reconciling...")

        store_id = sanitize_store_id(name)
        store_namespace = f"store-{store_id}"
        release_name = f"store-{store_id}"
        base_domain = spec.get('baseDomain', BASE_DOMAIN)

        try:
            # Check if release exists
            release_exists = await check_helm_release_exists(release_name, store_namespace)

            if not release_exists:
                logger.warning(f"[{name}] Release doesn't exist, may need to re-provision")
                patch['status'] = build_status_update(
                    phase='Failed',
                    message='Controller restarted during provisioning, release not found'
                )
                return

            # Check if WordPress deployment is ready
            wordpress_deployment = f"{release_name}-wordpress"
            deployment_ready = await check_deployment_ready(wordpress_deployment, store_namespace)

            if not deployment_ready:
                logger.info(f"[{name}] Deployment not ready yet, keeping current phase")
                return

            # Check if setup job completed
            setup_job_name = f"{release_name}-wordpress-setup"
            exists, succeeded = await check_job_completed(setup_job_name, store_namespace)

            if exists and succeeded:
                # Everything is ready!
                logger.info(f"[{name}] Store is actually ready, updating status")

                store_url = f"http://{store_id}.{base_domain}"
                admin_url = f"http://{store_id}.{base_domain}/wp-admin"
                ready_at = get_timestamp()

                patch['status'] = build_status_update(
                    phase='Ready',
                    url=store_url,
                    admin_url=admin_url,
                    message='Store is ready and accessible',
                    ready_at=ready_at
                )

                kopf.info(
                    spec,
                    reason='Reconciled',
                    message=f'Store reconciled to Ready state after controller restart'
                )
            else:
                logger.info(f"[{name}] Setup job not completed yet, keeping current phase")

        except Exception as e:
            logger.error(f"[{name}] Error during reconciliation: {e}")
            logger.exception(e)

    elif current_phase == 'Ready':
        logger.info(f"[{name}] Store is already Ready, no action needed")

    elif current_phase == 'Failed':
        logger.info(f"[{name}] Store is in Failed state, no automatic recovery")

    else:
        logger.warning(f"[{name}] Unknown phase: {current_phase}")


if __name__ == '__main__':
    # This won't be used when run via kopf CLI, but useful for testing
    logger.info("Store Provisioning Controller")
    logger.info("Run with: kopf run controller.py --verbose")
