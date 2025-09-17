# ============================================
# Simplified Multi-Stage Dockerfile
# Supports: Development, Production, Lambda
# ============================================

# Build arguments
ARG TARGETPLATFORM
ARG BUILDPLATFORM
ARG BUILD_STAGE=development

# ============================================
# Stage 1: Base - Common dependencies
# ============================================
FROM python:3.13-slim AS base

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    libffi-dev \
    libssl-dev \
    libpq-dev \
    libpq5 \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set common environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on

# ============================================
# Stage 2: Builder - Create wheels for faster builds
# ============================================
FROM base AS builder

WORKDIR /wheels

# Copy requirements and build wheels
COPY requirements*.txt ./
RUN pip install --upgrade pip wheel && \
    pip wheel --no-cache-dir --wheel-dir=/wheels \
    -r requirements.txt \
    -r requirements-dev.txt

# ============================================
# Stage 3: Development
# ============================================
FROM base AS development

WORKDIR /app

# Copy wheels and install dependencies
COPY --from=builder /wheels /wheels
COPY requirements*.txt ./
RUN pip install --no-cache-dir --find-links=/wheels \
    -r requirements.txt \
    -r requirements-dev.txt \
    gunicorn==23.0.0 \
    gevent==24.11.1 \
    && rm -rf /wheels

# Copy application code
COPY . .

# Copy and setup entrypoint
COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Development environment variables
ENV FLASK_APP=wsgi:app \
    FLASK_ENV=development \
    PYTHONPATH=/app

EXPOSE 5000
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--worker-class", "gevent", "--workers", "4", "wsgi:app"]

# ============================================
# Stage 4: Production (Container)
# ============================================
FROM base AS production

WORKDIR /app

# Copy wheels and install production dependencies only
COPY --from=builder /wheels /wheels
COPY requirements.txt ./
RUN pip install --no-cache-dir --find-links=/wheels \
    -r requirements.txt \
    gunicorn==23.0.0 \
    gevent==24.11.1 \
    && rm -rf /wheels

# Copy application code
COPY . .

# Copy and setup entrypoint
COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Production environment variables
ENV FLASK_APP=wsgi:app \
    FLASK_ENV=production \
    PYTHONPATH=/app

EXPOSE 5000
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--worker-class", "gevent", "--workers", "4", "wsgi:app"]

# ============================================
# Stage 5: Lambda
# ============================================
FROM public.ecr.aws/lambda/python:3.13 AS lambda

# Install system dependencies
RUN dnf install -y gcc python3-devel libffi-devel openssl-devel \
    && dnf clean all \
    && rm -rf /var/cache/dnf

WORKDIR ${LAMBDA_TASK_ROOT}

# Copy wheels and install production dependencies
COPY --from=builder /wheels /wheels
COPY requirements.txt ./
RUN pip install --no-cache-dir --find-links=/wheels \
    -r requirements.txt \
    && rm -rf /wheels

# Copy application code
COPY . ${LAMBDA_TASK_ROOT}

# Set permissions and create directories
RUN mkdir -p ${LAMBDA_TASK_ROOT}/instance \
    && chown -R 1001:0 ${LAMBDA_TASK_ROOT} \
    && chmod -R 755 ${LAMBDA_TASK_ROOT} \
    && chmod +x ${LAMBDA_TASK_ROOT}/entrypoint.sh

# Lambda environment variables
ENV PYTHONPATH=/var/task \
    LAMBDA_TASK_ROOT=/var/task \
    FLASK_APP=wsgi:app \
    FLASK_ENV=production

USER 1001
CMD ["wsgi.lambda_handler"]
