# ATLAS - Otonom AI Is Ortagi Sistemi
# Multi-stage build ile optimize edilmis Docker image

FROM python:3.11-slim AS base

# Sistem bagimlilikları
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Python ortam ayarlari
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# --- Builder katmani ---
FROM base AS builder

COPY pyproject.toml ./
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir .

# --- Production katmani ---
FROM base AS production

# Builder'dan kurulu paketleri kopyala
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Uygulama dosyalarini kopyala
COPY app/ ./app/
COPY alembic/ ./alembic/
COPY alembic.ini ./
COPY scripts/ ./scripts/

# Guvenlik: root olmayan kullanici
RUN groupadd -r atlas && useradd -r -g atlas atlas
USER atlas

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import httpx; r = httpx.get('http://localhost:8000/health'); r.raise_for_status()"]

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
