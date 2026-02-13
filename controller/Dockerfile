# Controller Dockerfile
# Build context: controller/ directory
# NOTE: setup-cluster.sh copies store-chart/ into controller/ before building
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies (helm and kubectl)
RUN apt-get update && apt-get install -y \
    curl \
    gcc \
    apt-transport-https \
    ca-certificates \
    gnupg \
    && curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash \
    && curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl" \
    && install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl \
    && rm kubectl \
    && rm -rf /var/lib/apt/lists/*

# Verify installations
RUN helm version --short && kubectl version --client

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY controller.py .

# Copy the store-chart into the image (copied by setup-cluster.sh before build)
# This allows the controller to run helm install without external dependencies
COPY store-chart/ /charts/store-chart/

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV STORE_CHART_PATH=/charts/store-chart
ENV BASE_DOMAIN=local.store
ENV PLATFORM_NAMESPACE=store-platform

# Run the kopf operator
CMD ["kopf", "run", "--standalone", "--verbose", "/app/controller.py"]
