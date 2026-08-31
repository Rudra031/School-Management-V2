# Multi-stage optimized Dockerfile for Horizon School ERP
FROM python:3.12-slim AS base

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Collect static files
RUN python manage.py collectstatic --noinput

# Expose Gunicorn port
EXPOSE 8000

# Start Gunicorn server
CMD ["gunicorn", "--config", "gunicorn.conf.py", "config.wsgi:application"]
