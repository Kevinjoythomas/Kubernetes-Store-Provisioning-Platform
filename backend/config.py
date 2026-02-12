"""
Configuration for Flask API
"""

import os


class Config:
    """Base configuration"""

    # Flask configuration
    DEBUG = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    TESTING = os.getenv('FLASK_TESTING', 'False').lower() == 'true'
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')

    # Kubernetes configuration
    PLATFORM_NAMESPACE = os.getenv('PLATFORM_NAMESPACE', 'platform')
    K8S_IN_CLUSTER = os.getenv('K8S_IN_CLUSTER', 'true').lower() == 'true'

    # Store CRD configuration
    STORE_CRD_GROUP = 'platform.urumi.io'
    STORE_CRD_VERSION = 'v1'
    STORE_CRD_PLURAL = 'stores'

    # Store configuration
    BASE_DOMAIN = os.getenv('BASE_DOMAIN', 'local.store')
    DEFAULT_STORE_TYPE = 'woocommerce'
    MAX_STORES_PER_USER = int(os.getenv('MAX_STORES_PER_USER', '10'))

    # API configuration
    API_TITLE = 'Store Provisioning Platform API'
    API_VERSION = 'v1'
    RATE_LIMIT = os.getenv('RATE_LIMIT', '10/minute')

    # CORS configuration
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', '*')


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    K8S_IN_CLUSTER = False  # Use kubeconfig in development


class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    K8S_IN_CLUSTER = True  # Use in-cluster config in production


# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': Config
}
