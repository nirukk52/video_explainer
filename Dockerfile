# Video Explainer System
# Multi-stage build for Python + Node.js (Motion Canvas)

# Stage 1: Node.js for Motion Canvas
FROM node:20-slim AS node-builder

WORKDIR /app/animations

# Copy animation project files
COPY animations/package*.json ./
RUN npm ci --production

COPY animations/ ./

# Stage 2: Python application
FROM python:3.10-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js for Motion Canvas rendering
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy Python requirements and install
COPY pyproject.toml ./
RUN pip install --no-cache-dir -e .

# Copy the application code
COPY src/ ./src/
COPY config.yaml ./
COPY templates/ ./templates/

# Copy Node.js dependencies from builder
COPY --from=node-builder /app/animations ./animations

# Create output directories
RUN mkdir -p output/scripts output/audio output/video output/storyboards

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Default command
CMD ["python", "-m", "src.cli"]
