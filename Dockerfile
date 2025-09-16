# Lightweight Python
FROM python:3.11-slim

# Prevent Python buffering
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

# System deps (optional but helpful)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc curl && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install deps
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy app
COPY . /app

# Gunicorn server
# server:app  -> looks for "app" in server.py
#CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 120 server:app
CMD exec gunicorn --bind :$PORT --workers 2 --threads 4 --timeout 0 server:app

