# Stage 1: Build dependencies and install Python packages
FROM python:3.13 AS builder

WORKDIR /app

# Install system dependencies required for building Python packages
# 'build-essential' typically includes gcc and python3-dev equivalents
RUN apt-get update && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements.txt and install Python dependencies into a wheelhouse
COPY requirements.txt .
RUN pip wheel --no-cache-dir --wheel-dir /tmp/wheels -r requirements.txt --no-binary brotli

# Stage 2: Create the final runtime image
FROM python:3.13-alpine

WORKDIR /app

# Install build dependencies required for certain Python packages to compile from source
RUN apk add --no-cache gcc python3-dev musl-dev linux-headers \
    && rm -rf /var/cache/apk/*

# Copy only the installed Python packages from the builder stage
COPY --from=builder /tmp/wheels /tmp/wheels
COPY requirements.txt .
RUN ls -l /app && \
    pip install --no-cache-dir --find-links /tmp/wheels -r requirements.txt && \
    rm -rf /tmp/wheels

# Copy the rest of the application
COPY . .

# Set environment variables
ENV FLASK_APP=wsgi.py
ENV FLASK_ENV=development

# Create a volume for the database
VOLUME /app/instance

EXPOSE 5000

# Run the application
CMD ["sh", "-c", "flask init-db && flask run --host=0.0.0.0"]
