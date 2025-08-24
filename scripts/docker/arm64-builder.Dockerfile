FROM --platform=linux/arm64 python:3.13-slim

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

# Copy the package script and requirements
COPY requirements.txt .

# Install the package in a virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --upgrade pip setuptools wheel

# Install requirements
RUN pip install -r requirements.txt --target /opt/python

# Install msgspec specifically for ARM64
RUN pip install msgspec==0.19.0 --target /opt/python

# Create the layer zip
RUN cd /opt && zip -r /layer.zip python/

# The output will be available at /layer.zip
