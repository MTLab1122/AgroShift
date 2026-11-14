# Multi-stage Dockerfile for AgroShift Backend
FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY pyproject.toml .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
    fastapi \
    uvicorn \
    httpx \
    pydantic \
    jsonschema \
    pytest \
    pytest-asyncio

# Copy application source
COPY backend/ backend/
COPY shared/ shared/
COPY data/ data/
COPY docs/ docs/

# Expose FastAPI port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run uvicorn server
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
