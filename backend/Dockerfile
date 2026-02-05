# syntax=docker/dockerfile:1
FROM python:3.11-slim

WORKDIR /app

# Optional but safe: some libs may need build tools
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy deps first for caching
COPY backend/requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY backend/app ./app

EXPOSE 8000



COPY backend/healthcheck.py .
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python healthcheck.py || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

COPY storage ./storage
ENV KB_STORAGE_DIR=/app/storage

