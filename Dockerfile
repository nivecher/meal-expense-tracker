# ============================================
# Stage 1: Builder - Install build dependencies
# ============================================
# Build arguments for platform specification
ARG TARGETPLATFORM
ARG BUILDPLATFORM
FROM python:3.13-slim AS builder

# Install build dependencies for psycopg2-binary and other Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    python3-dev \
    libssl-dev \
    libffi-dev \
    libpq-dev \
    libpq5 \
    postgresql-common \
    postgresql-client-common \
    && rm -rf /var/lib/apt/lists/*

# Create directory for wheels
WORKDIR /wheels

# Copy requirements files
COPY requirements*.txt /tmp/

# Install build dependencies and create wheels
COPY requirements*.txt /tmp/
RUN pip install --upgrade pip wheel \
    && cd /tmp \
    && pip wheel --no-cache-dir --wheel-dir=/wheels \
    -r requirements.txt \
    -r requirements-dev.txt \
    && cp /tmp/requirements*.txt /wheels/

# ============================================
# Stage 2: Development - For local development
# ============================================
FROM python:3.13-slim AS development

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    FLASK_APP=wsgi:app \
    FLASK_ENV=development \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy wheels and requirements from builder
COPY --from=builder /wheels /wheels
COPY --from=builder /wheels/requirements*.txt ./


# Install application dependencies
RUN pip install --no-cache-dir --find-links=/wheels \
    -r requirements.txt \
    -r requirements-dev.txt \
    gunicorn==23.0.0 \
    gevent==24.11.1 \
    && rm -rf /wheels

# Copy application code
COPY . .

# Expose port for local development
EXPOSE 5000

# Install PostgreSQL client for database operations
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy entrypoint script and make it executable
COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Set environment variables for the application
ENV FLASK_APP=wsgi:app \
    FLASK_ENV=production \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    # Default database configuration (can be overridden in docker-compose)
    DB_ENGINE=postgresql \
    DB_HOST=db \
    DB_PORT=5433 \
    DB_NAME=meal_expenses \
    DB_USERNAME=mealuser \
    DB_PASSWORD=mealpassword \
    # Admin user configuration
    DEFAULT_ADMIN_USERNAME=admin \
    DEFAULT_ADMIN_EMAIL=admin@example.com \
    DEFAULT_ADMIN_PASSWORD=admin123 \
    # Set to 'true' to skip database initialization
    SKIP_DB_INIT=false

# Set the working directory
WORKDIR /app

# Expose the port the app runs on
EXPOSE 5000

# Command to run the application with entrypoint
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--worker-class", "gevent", "--workers", "4", "wsgi:app"]

# ============================================
# Stage 3: Production - For Lambda deployment
# ============================================
# Note: AWS Lambda requires linux/amd64 for Python 3.13
FROM public.ecr.aws/lambda/python:3.13 AS production

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/var/task \
    LAMBDA_TASK_ROOT=/var/task \
    FLASK_APP=wsgi:app \
    FLASK_ENV=production \
    AWS_LAMBDA_FUNCTION_MEMORY_SIZE=1024 \
    AWS_LAMBDA_FUNCTION_TIMEOUT=30

# Set working directory
WORKDIR ${LAMBDA_TASK_ROOT}

# Install system dependencies
RUN dnf install -y gcc python3-devel libffi-devel openssl-devel \
    && dnf clean all \
    && rm -rf /var/cache/dnf

# Install runtime dependencies from wheels
COPY --from=builder /wheels /wheels
COPY --from=builder /wheels/requirements*.txt .

# Install only production dependencies
RUN pip install --no-cache-dir --find-links=/wheels \
    -r requirements.txt \
    && rm -rf /wheels /tmp/* /var/tmp/*

# Copy application code
COPY . ${LAMBDA_TASK_ROOT}

# Create necessary directories and set permissions
RUN mkdir -p ${LAMBDA_TASK_ROOT}/instance \
    && chown -R 1001:0 ${LAMBDA_TASK_ROOT} \
    && chmod -R 755 ${LAMBDA_TASK_ROOT} \
    && find ${LAMBDA_TASK_ROOT} -type d -exec chmod 755 {} \; \
    && find ${LAMBDA_TASK_ROOT} -type f -exec chmod 644 {} \; \
    && chmod +x ${LAMBDA_TASK_ROOT}/entrypoint.sh \
    && chmod -R g=u ${LAMBDA_TASK_ROOT} \
    && chmod -R 755 /var/tmp

# Run as non-root user for security
USER 1001

# Set the CMD for Lambda (this should point to your Lambda handler function)
# Example: CMD ["your_module.handler"]
CMD ["wsgi.lambda_handler"]

# Health check (optional, for container-based deployments)
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1
