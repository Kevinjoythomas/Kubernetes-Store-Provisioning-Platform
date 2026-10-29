"""
Store Provisioning Platform - Flask API
Backend API for managing Store CRDs in Kubernetes
"""

import logging
import os
import re
import secrets
from datetime import datetime

from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from kubernetes import client, config as k8s_config
from kubernetes.client.rest import ApiException

from config import Config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.config.from_object(Config)

# Initialize CORS
CORS(app, origins=app.config['CORS_ORIGINS'])

# Initialize rate limiter
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=[app.config['RATE_LIMIT']],
    storage_uri="memory://"
)

# Initialize Kubernetes client
try:
    if app.config['K8S_IN_CLUSTER']:
        logger.info("Loading in-cluster Kubernetes configuration")
        k8s_config.load_incluster_config()
    else:
        logger.info("Loading Kubernetes configuration from kubeconfig")
        k8s_config.load_kube_config()

    # Create CustomObjectsApi instance
    k8s_api = client.CustomObjectsApi()
    logger.info("Kubernetes client initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize Kubernetes client: {e}")
    k8s_api = None


# ============================================================================
# Helper Functions
# ============================================================================

def slugify(text: str) -> str:
    """
    Convert text to a URL-friendly slug.
    - Lowercase
    - Replace spaces with hyphens
    - Remove non-alphanumeric characters except hyphens
    """
    # Lowercase
    text = text.lower()

    # Replace spaces with hyphens
    text = text.replace(' ', '-')

    # Remove non-alphanumeric characters except hyphens
    text = re.sub(r'[^a-z0-9-]', '', text)

    # Remove consecutive hyphens
    text = re.sub(r'-+', '-', text)

    # Strip leading/trailing hyphens
    text = text.strip('-')

    return text


def generate_store_id(display_name: str) -> str:
    """
    Generate a unique store ID from display name.
    - Slugify the display name
    - Append 6 random alphanumeric characters
    - Ensure max 20 characters total
    - Lowercase
    """
    # Slugify display name
    slug = slugify(display_name)

    # Generate random suffix
    random_suffix = secrets.token_hex(3)  # 6 characters

    # Combine slug and suffix
    if slug:
        # Truncate slug to leave room for suffix + hyphen
        max_slug_length = 20 - len(random_suffix) - 1
        slug = slug[:max_slug_length].rstrip('-')
        store_id = f"{slug}-{random_suffix}"
    else:
        # If slug is empty, just use "store-" + random
        store_id = f"store-{random_suffix}"

    # Ensure max 20 characters
    store_id = store_id[:20].rstrip('-')

    return store_id


def format_store(store_obj: dict) -> dict:
    """
    Format a Store CRD object into API response format.
    """
    metadata = store_obj.get('metadata', {})
    spec = store_obj.get('spec', {})
    status = store_obj.get('status', {})

    return {
        'id': metadata.get('name'),
        'displayName': spec.get('displayName', metadata.get('name')),
        'storeType': spec.get('storeType'),
        'phase': status.get('phase', 'Unknown'),
        'url': status.get('url'),
        'adminUrl': status.get('adminUrl'),
        'message': status.get('message'),
        'createdAt': metadata.get('creationTimestamp'),
        'readyAt': status.get('readyAt'),
        'events': status.get('events', [])
    }


def validate_store_input(data: dict) -> tuple[bool, str]:
    """
    Validate store creation input.

    Returns:
        tuple: (is_valid, error_message)
    """
    # Check displayName
    display_name = data.get('displayName', '').strip()
    if not display_name:
        return False, "displayName is required"

    if len(display_name) < 1 or len(display_name) > 50:
        return False, "displayName must be between 1 and 50 characters"

    # Check storeType
    store_type = data.get('storeType', '').strip().lower()
    if not store_type:
        return False, "storeType is required"

    if store_type not in ['woocommerce', 'medusa']:
        return False, "storeType must be 'woocommerce' or 'medusa'"

    # Check if medusa (not yet implemented)
    if store_type == 'medusa':
        return False, "Medusa support coming soon , architecture ready but not yet implemented"

    return True, ""


def get_store_count() -> int:
    """
    Get the current number of stores.
    """
    try:
        stores = k8s_api.list_namespaced_custom_object(
            group=app.config['STORE_CRD_GROUP'],
            version=app.config['STORE_CRD_VERSION'],
            namespace=app.config['PLATFORM_NAMESPACE'],
            plural=app.config['STORE_CRD_PLURAL']
        )
        return len(stores.get('items', []))
    except Exception as e:
        logger.error(f"Error getting store count: {e}")
        return 0


# ============================================================================
# Request Logging Middleware
# ============================================================================

@app.before_request
def log_request():
    """Log all incoming requests"""
    logger.info(f"{request.method} {request.path} - {request.remote_addr}")


@app.after_request
def log_response(response):
    """Log all outgoing responses"""
    logger.info(f"{request.method} {request.path} - {response.status_code}")
    return response


# ============================================================================
# Error Handlers
# ============================================================================

@app.errorhandler(400)
def bad_request(error):
    """Handle 400 Bad Request errors"""
    return jsonify({
        'error': 'Bad Request',
        'message': str(error.description) if hasattr(error, 'description') else 'Invalid request'
    }), 400


@app.errorhandler(404)
def not_found(error):
    """Handle 404 Not Found errors"""
    return jsonify({
        'error': 'Not Found',
        'message': 'The requested resource was not found'
    }), 404


@app.errorhandler(429)
def rate_limit_exceeded(error):
    """Handle 429 Too Many Requests errors"""
    return jsonify({
        'error': 'Too Many Requests',
        'message': 'Rate limit exceeded. Please try again later.'
    }), 429


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 Internal Server Error"""
    logger.error(f"Internal server error: {error}")
    return jsonify({
        'error': 'Internal Server Error',
        'message': 'An unexpected error occurred'
    }), 500


# ============================================================================
# API Endpoints
# ============================================================================

@app.route('/api/health', methods=['GET'])
def health():
    """
    Health check endpoint.
    Returns 200 if the API is healthy.
    """
    return jsonify({'status': 'healthy'}), 200


@app.route('/api/stores', methods=['GET'])
def list_stores():
    """
    List all Store CRs in the platform namespace.

    Returns:
        200: Array of stores sorted by createdAt descending
        500: Error listing stores
    """
    try:
        # Query all Store CRDs
        stores = k8s_api.list_namespaced_custom_object(
            group=app.config['STORE_CRD_GROUP'],
            version=app.config['STORE_CRD_VERSION'],
            namespace=app.config['PLATFORM_NAMESPACE'],
            plural=app.config['STORE_CRD_PLURAL']
        )

        # Format stores
        formatted_stores = [format_store(store) for store in stores.get('items', [])]

        # Sort by createdAt descending (newest first)
        formatted_stores.sort(
            key=lambda x: x.get('createdAt', ''),
            reverse=True
        )

        return jsonify(formatted_stores), 200

    except ApiException as e:
        logger.error(f"Kubernetes API error listing stores: {e}")
        return jsonify({
            'error': 'Failed to list stores',
            'message': str(e.reason)
        }), 500
    except Exception as e:
        logger.error(f"Error listing stores: {e}")
        return jsonify({
            'error': 'Failed to list stores',
            'message': str(e)
        }), 500


@app.route('/api/stores', methods=['POST'])
def create_store():
    """
    Create a new Store CR.

    Body:
        displayName: string (1-50 chars, required)
        storeType: "woocommerce" or "medusa" (required)

    Returns:
        201: Store created successfully
        400: Invalid input
        429: Too many stores
        409: Store with same ID already exists (idempotent success)
        500: Error creating store
    """
    try:
        # Get request data
        data = request.get_json()
        if not data:
            return jsonify({
                'error': 'Invalid request',
                'message': 'Request body must be JSON'
            }), 400

        # Validate input
        is_valid, error_message = validate_store_input(data)
        if not is_valid:
            return jsonify({
                'error': 'Validation error',
                'message': error_message
            }), 400

        # Check store count limit
        store_count = get_store_count()
        if store_count >= app.config['MAX_STORES_PER_USER']:
            return jsonify({
                'error': 'Store limit reached',
                'message': f'Maximum {app.config["MAX_STORES_PER_USER"]} stores allowed'
            }), 429

        # Extract validated data
        display_name = data['displayName'].strip()
        store_type = data['storeType'].strip().lower()

        # Generate store ID
        store_id = generate_store_id(display_name)
        logger.info(f"Creating store with ID: {store_id}")

        # Create Store CR
        store_cr = {
            'apiVersion': f"{app.config['STORE_CRD_GROUP']}/{app.config['STORE_CRD_VERSION']}",
            'kind': 'Store',
            'metadata': {
                'name': store_id,
                'namespace': app.config['PLATFORM_NAMESPACE'],
                'labels': {
                    'app.kubernetes.io/managed-by': 'store-platform'
                }
            },
            'spec': {
                'storeType': store_type,
                'displayName': display_name,
                'baseDomain': app.config['BASE_DOMAIN']
            }
        }

        # Create the Store CRD
        created_store = k8s_api.create_namespaced_custom_object(
            group=app.config['STORE_CRD_GROUP'],
            version=app.config['STORE_CRD_VERSION'],
            namespace=app.config['PLATFORM_NAMESPACE'],
            plural=app.config['STORE_CRD_PLURAL'],
            body=store_cr
        )

        logger.info(f"Store created successfully: {store_id}")

        # Return formatted store
        return jsonify(format_store(created_store)), 201

    except ApiException as e:
        if e.status == 409:
            # Store already exists - return idempotent success
            logger.warning(f"Store already exists (409): {data.get('displayName')}")
            try:
                # Fetch the existing store
                existing_store = k8s_api.get_namespaced_custom_object(
                    group=app.config['STORE_CRD_GROUP'],
                    version=app.config['STORE_CRD_VERSION'],
                    namespace=app.config['PLATFORM_NAMESPACE'],
                    plural=app.config['STORE_CRD_PLURAL'],
                    name=store_id
                )
                return jsonify(format_store(existing_store)), 201
            except Exception:
                pass

        logger.error(f"Kubernetes API error creating store: {e}")
        return jsonify({
            'error': 'Failed to create store',
            'message': str(e.reason)
        }), 500
    except Exception as e:
        logger.error(f"Error creating store: {e}")
        return jsonify({
            'error': 'Failed to create store',
            'message': str(e)
        }), 500


@app.route('/api/stores/<store_id>', methods=['GET'])
def get_store(store_id):
    """
    Get a single Store CR by ID.

    Args:
        store_id: The store ID (metadata.name)

    Returns:
        200: Store details
        404: Store not found
        500: Error getting store
    """
    try:
        # Get the Store CRD
        store = k8s_api.get_namespaced_custom_object(
            group=app.config['STORE_CRD_GROUP'],
            version=app.config['STORE_CRD_VERSION'],
            namespace=app.config['PLATFORM_NAMESPACE'],
            plural=app.config['STORE_CRD_PLURAL'],
            name=store_id
        )

        return jsonify(format_store(store)), 200

    except ApiException as e:
        if e.status == 404:
            return jsonify({
                'error': 'Store not found',
                'message': f'Store with ID {store_id} does not exist'
            }), 404

        logger.error(f"Kubernetes API error getting store: {e}")
        return jsonify({
            'error': 'Failed to get store',
            'message': str(e.reason)
        }), 500
    except Exception as e:
        logger.error(f"Error getting store: {e}")
        return jsonify({
            'error': 'Failed to get store',
            'message': str(e)
        }), 500


@app.route('/api/stores/<store_id>', methods=['DELETE'])
def delete_store(store_id):
    """
    Delete a Store CR by ID.
    The kopf controller will handle actual cleanup of resources.

    Args:
        store_id: The store ID (metadata.name)

    Returns:
        200: Store deletion initiated
        404: Store not found
        500: Error deleting store
    """
    try:
        # Delete the Store CRD
        k8s_api.delete_namespaced_custom_object(
            group=app.config['STORE_CRD_GROUP'],
            version=app.config['STORE_CRD_VERSION'],
            namespace=app.config['PLATFORM_NAMESPACE'],
            plural=app.config['STORE_CRD_PLURAL'],
            name=store_id
        )

        logger.info(f"Store deletion initiated: {store_id}")

        return jsonify({
            'status': 'deleting',
            'message': f'Store {store_id} deletion initiated'
        }), 200

    except ApiException as e:
        if e.status == 404:
            return jsonify({
                'error': 'Store not found',
                'message': f'Store with ID {store_id} does not exist'
            }), 404

        logger.error(f"Kubernetes API error deleting store: {e}")
        return jsonify({
            'error': 'Failed to delete store',
            'message': str(e.reason)
        }), 500
    except Exception as e:
        logger.error(f"Error deleting store: {e}")
        return jsonify({
            'error': 'Failed to delete store',
            'message': str(e)
        }), 500


# ============================================================================
# Application Entry Point
# ============================================================================

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    logger.info(f"Starting Flask API on port {port}")
    logger.info(f"Platform namespace: {app.config['PLATFORM_NAMESPACE']}")
    logger.info(f"Base domain: {app.config['BASE_DOMAIN']}")
    logger.info(f"Max stores per user: {app.config['MAX_STORES_PER_USER']}")
    logger.info(f"Rate limit: {app.config['RATE_LIMIT']}")

    app.run(host='0.0.0.0', port=port, debug=app.config['DEBUG'])
