# ============================================
# Optimized Multi-Stage Dockerfile
# Fast builds with proper layer caching
# ============================================

# Build arguments
ARG TARGETPLATFORM
ARG BUILDPLATFORM
ARG BUILD_STAGE=development

# ============================================
# Stage 1: Base - Minimal system dependencies
# ============================================
FROM python:3.13-slim AS base

# Install only essential system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    libffi-dev \
    libssl-dev \
    libpq-dev \
    libpq5 \
    postgresql-client \
    curl \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Set common environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# ============================================
# Stage 2: Dependencies - Separate layer for caching
# ============================================
FROM base AS dependencies

WORKDIR /app

# Copy ONLY requirements files first (for better layer caching)
COPY requirements.txt requirements-dev.txt ./

# Install production dependencies first (smaller, cached separately)
# Note: requirements.txt does NOT include EasyOCR/PyTorch - these are only in requirements/scripts.txt
# for standalone utility scripts. Production app uses AWS Textract for OCR.
RUN pip install --no-cache-dir --upgrade pip wheel && \
    pip install --no-cache-dir -r requirements.txt

# ============================================
# Stage 3: Development Dependencies
# ============================================
FROM dependencies AS development-deps

# Install development dependencies (separate layer)
RUN pip install --no-cache-dir -r requirements-dev.txt

# ============================================
# Stage 4: Development (Fast)
# ============================================
FROM development-deps AS development

# Copy application code (after dependencies are cached)
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
# Stage 5: Production (Minimal)
# ============================================
FROM dependencies AS production

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
# Stage 6: Lambda Builder (with build tools)
# ============================================
FROM public.ecr.aws/lambda/python:3.13 AS lambda-builder

# Install system dependencies for building Python packages (build-time only)
RUN dnf install -y \
    gcc \
    python3-devel \
    libffi-devel \
    openssl-devel \
    postgresql-devel \
    poppler-utils \
    && dnf clean all

WORKDIR ${LAMBDA_TASK_ROOT}

# Copy requirements file
COPY requirements.txt ${LAMBDA_TASK_ROOT}/

# Install Python dependencies (compiled packages will be copied to runtime stage)
RUN pip install --no-cache-dir -r requirements.txt

# ============================================
# Stage 7: Lambda (runtime only, no build tools)
# ============================================
FROM public.ecr.aws/lambda/python:3.13 AS lambda

# Install only runtime system dependencies (no build tools)
RUN dnf install -y \
    postgresql-libs \
    poppler-utils \
    && dnf clean all

WORKDIR ${LAMBDA_TASK_ROOT}

# Copy installed Python packages from builder stage (not build tools)
COPY --from=lambda-builder /var/lang/lib/python3.13/site-packages /var/lang/lib/python3.13/site-packages

# Copy application code
COPY app/ ${LAMBDA_TASK_ROOT}/app/
COPY wsgi.py ${LAMBDA_TASK_ROOT}/
COPY lambda_handler.py ${LAMBDA_TASK_ROOT}/
COPY lambda_init.py ${LAMBDA_TASK_ROOT}/
COPY config.py ${LAMBDA_TASK_ROOT}/
COPY migrations/ ${LAMBDA_TASK_ROOT}/migrations/

# Create necessary directories and set permissions
RUN mkdir -p ${LAMBDA_TASK_ROOT}/instance \
    ${LAMBDA_TASK_ROOT}/migrations/versions \
    && chown -R 1001:0 ${LAMBDA_TASK_ROOT}

# Set proper permissions
RUN chmod 755 ${LAMBDA_TASK_ROOT} && \
    chmod 644 ${LAMBDA_TASK_ROOT}/*.py && \
    chmod 755 ${LAMBDA_TASK_ROOT}/app && \
    chmod 644 ${LAMBDA_TASK_ROOT}/app/*.py && \
    chmod 755 ${LAMBDA_TASK_ROOT}/app/*/

# Create necessary __init__.py files (only for modules that don't have them)
RUN echo "" > ${LAMBDA_TASK_ROOT}/__init__.py

# Copy and set up entrypoint if it exists
RUN if [ -f "${LAMBDA_TASK_ROOT}/docker-entrypoint.sh" ]; then \
        chmod +x ${LAMBDA_TASK_ROOT}/docker-entrypoint.sh; \
    fi

# Lambda environment variables
ENV PYTHONPATH=/var/task \
    LAMBDA_TASK_ROOT=/var/task \
    FLASK_APP=wsgi:app \
    FLASK_ENV=production \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Switch to non-root user for security
USER 1001

# Command to run the Lambda function (AWS Lambda Python base image - handler in exec form)
CMD ["wsgi.lambda_handler"]
