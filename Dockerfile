# ============================================
# Stage 1: Builder - Install build dependencies
# ============================================
FROM python:3.13 AS builder

WORKDIR /app

# Install system dependencies for building
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    python3-dev \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements files
COPY requirements/ ./requirements/

# Create wheels for all requirements
RUN pip wheel --no-cache-dir --wheel-dir /tmp/wheels \
    -r requirements/base.in \
    -r requirements/prod.in \
    gunicorn \
    gevent \
    --no-binary brotli

# ============================================
# Stage 2: Development
# ============================================
FROM python:3.13-slim AS development

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copy wheels from builder
COPY --from=builder /tmp/wheels /tmp/wheels
COPY --from=builder /app/requirements /app/requirements

# Install Python dependencies
RUN pip install --no-cache-dir --find-links /tmp/wheels \
    -r requirements/base.in \
    -r requirements/dev.in \
    -r requirements/security.in \
    gunicorn \
    gevent \
    && rm -rf /tmp/wheels

# Copy application code
COPY . .

# Set environment variables
ENV FLASK_APP=wsgi.py
ENV FLASK_ENV=development
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Expose port for development
EXPOSE 5001

# Create necessary directories
RUN mkdir -p /app/instance

# Command for development
CMD ["flask", "run", "--host=0.0.0.0", "--port=5001"]

# ============================================
# Stage 3: Production
# ============================================
FROM python:3.13-slim AS production

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copy wheels from builder
COPY --from=builder /tmp/wheels /tmp/wheels
COPY --from=builder /app/requirements /app/requirements

# Install production requirements
RUN pip install --no-cache-dir --find-links /tmp/wheels \
    -r requirements/base.in \
    -r requirements/prod.in \
    gunicorn \
    gevent \
    && rm -rf /tmp/wheels

# Copy application code
COPY . .

# Set environment variables
ENV FLASK_APP=wsgi.py
ENV FLASK_ENV=production
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Create necessary directories and set permissions
RUN mkdir -p /app/instance \
    && chown -R nobody:nogroup /app \
    && chmod -R 755 /app

# Switch to non-root user
USER nobody

# Expose port
EXPOSE 5001

# Command to run the application
CMD ["gunicorn", "--bind", "0.0.0.0:5001", "--worker-class", "gevent", "--workers", "4", "wsgi:app"]

# Set default target (production)
FROM production
