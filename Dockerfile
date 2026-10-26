# syntax=docker/dockerfile:1
FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Force IPv4 precedence in glibc getaddrinfo to prevent IPv6 routing issues on cloud container networks.
RUN echo "precedence ::ffff:0:0/96 100" >> /etc/gai.conf

# Install deps first for layer caching.
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app ./app
COPY locustfile.py pyproject.toml ./

# Run as non-root.
RUN useradd --create-home --uid 1000 appuser
USER appuser

EXPOSE 8000 10000

# Default command runs the API; reads dynamic PORT and WEB_CONCURRENCY from the environment
# with fallbacks for local / docker-compose runs.
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers ${WEB_CONCURRENCY:-1} --proxy-headers --forwarded-allow-ips '*'"]
