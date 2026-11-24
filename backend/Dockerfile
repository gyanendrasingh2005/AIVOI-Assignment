# Multi-stage / Production Dockerfile for PharmaRCA Backend
FROM python:3.11-slim as base

# Prevents Python from writing pyc files and enables unbuffered stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

# Install system dependencies needed for asyncpg, psycopg2, cryptography, and healthchecks
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies in a virtual environment or directly into system
COPY requirements.txt /app/
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY . /app/

# Create a dedicated non-root user for security compliance (GxP / DevSecOps)
RUN groupadd -r pharmagroup && useradd -r -g pharmagroup -s /bin/false pharmauser && \
    mkdir -p /app/storage/evidence && \
    chown -R pharmauser:pharmagroup /app

USER pharmauser

# Health check to ensure service readiness
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2", "--proxy-headers", "--forwarded-allow-ips", "*"]

