# Use Python 3.12 slim base image
FROM python:3.12-slim

# Prevent Python from buffering stdout/stderr
ENV PYTHONUNBUFFERED=1
# Dockerfile
ENV POSTGRES_DSN=postgresql://neondb_owner:npg_2N4tvDmsuFiB@ep-summer-feather-adu6z5pt-pooler.c-2.us-east-1.aws.neon.tech/aaudating?sslmode=require

# Set working directory
WORKDIR /app

# Copy requirements first (cache layer)
COPY requirements.txt .

# Upgrade pip, setuptools, wheel, and install dependencies
RUN pip install --upgrade pip setuptools wheel \
    && pip install --no-cache-dir -r requirements.txt

# Copy the rest of your project (including main.py)
COPY . .

# Expose port (8080 matches the default in main.py)
EXPOSE 8080

# Command to run the bot using Gunicorn with the specialized aiohttp worker.
# This points to the synchronous factory function main:create_app.
CMD ["sh", "-c", "gunicorn bot:create_app --worker-class aiohttp.GunicornWebWorker --bind 0.0.0.0:${PORT:-8080}"]