# Backend API Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app.py config.py ./

# Expose Flask port
EXPOSE 5000

# Set environment variables
ENV FLASK_APP=app.py
ENV PYTHONUNBUFFERED=1
ENV K8S_IN_CLUSTER=true
ENV PLATFORM_NAMESPACE=store-platform
ENV BASE_DOMAIN=local.store

# Run with gunicorn for production
CMD ["gunicorn", "-w", "2", "-b", "0.0.0.0:5000", "app:app"]
