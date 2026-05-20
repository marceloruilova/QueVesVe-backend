# Dockerfile for Django backend

# 1. Install dependencies
FROM python:3.10-slim AS builder
WORKDIR /app
RUN pip install --no-cache-dir pipenv gunicorn
COPY Pipfile Pipfile.lock ./
RUN pipenv install --deploy --system --ignore-pipfile

# 2. Production image
FROM python:3.10-slim AS runner
WORKDIR /app

# Copy installed packages and binaries (including gunicorn) from builder
COPY --from=builder /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy project source
COPY . .

# Create dirs for static and media files
RUN mkdir -p /app/staticfiles /app/media

# Make entrypoint executable
RUN chmod +x /app/entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/app/entrypoint.sh"]
