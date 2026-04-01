# Family Hub Backend Dockerfile
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Set work directory
WORKDIR /app

# Install system dependencies (including postgresql-client for pg_dump)
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create backup directory
RUN mkdir -p /app/backups

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "app.main:socket_app", "--host", "0.0.0.0", "--port", "8000"]

