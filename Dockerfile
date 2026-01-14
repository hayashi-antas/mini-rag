FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8000

WORKDIR /app

# Install Python deps first for better layer caching
COPY requirements.txt /app/requirements.txt
RUN python -m pip install --upgrade pip && \
    python -m pip install -r /app/requirements.txt

# Copy application code
COPY rag/ /app/rag/
COPY templates/ /app/templates/
COPY docs/ /app/docs/
COPY config.env /app/config.env

# App Runner will route traffic to this port (configure in the service settings)
EXPOSE 8000

CMD ["sh", "-c", "uvicorn rag.api:app --host 0.0.0.0 --port ${PORT}"]

