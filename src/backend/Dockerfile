# =============================================================================
# MedBrief AI — Backend Production Dockerfile
# Step 15: Production Deployment Configuration
# =============================================================================

FROM python:3.11-slim as base

# Prevent Python from writing .pyc files and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PORT=8000

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY src/backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /app/requirements.txt

# Copy backend application source
COPY src/backend /app/src/backend

# Create private storage directory for medical PDFs
RUN mkdir -p /app/storage/documents

# Security: Create and run as unprivileged clinical system service user
RUN groupadd -r medbrief && useradd -r -g medbrief -d /app -s /sbin/nologin medbrief && \
    chown -R medbrief:medbrief /app

USER medbrief

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/health || exit 1

# Production startup command using dynamic port binding
CMD ["sh", "-c", "python -m uvicorn src.backend.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
