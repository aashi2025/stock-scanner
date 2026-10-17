# Production Dockerfile for Stock Confirmation Scanner
FROM python:3.13-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Environment Defaults
ENV PORT=8000
ENV HOST=0.0.0.0
ENV MARKET_DATA_PROVIDER=yahoo

EXPOSE 8000

# Start Uvicorn ASGI Server
CMD ["python", "-m", "uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
