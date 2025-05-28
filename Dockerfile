FROM python:3.13-slim

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    musl-dev \
    linux-headers-amd64 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Run the application
CMD ["python", "app/main.py"]

ENV FLASK_APP=app.py
ENV FLASK_ENV=production

# Create a volume for the database
VOLUME /app/instance

EXPOSE 5000

# Use environment variables from .env file
CMD ["sh", "-c", "flask init-db && flask run --host=0.0.0.0"] 