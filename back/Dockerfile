# API (FastAPI + SQLite). Build context: project root.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
# pytest is a dev dependency; skip it in the runtime image.
RUN grep -v '^pytest' requirements.txt > requirements.runtime.txt \
    && pip install --no-cache-dir -r requirements.runtime.txt

COPY src ./src
COPY docker/entrypoint.sh /entrypoint.sh

# /app/data holds the SQLite DB, the downloaded dataset and saved generations.
# Created and owned by the app user so a mounted named volume inherits the permissions.
RUN sed -i 's/\r$//' /entrypoint.sh && chmod +x /entrypoint.sh \
    && useradd --system --uid 1001 --home /app app \
    && mkdir -p /app/data && chown -R app:app /app/data

USER app
EXPOSE 8001
VOLUME ["/app/data"]

HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8001/api/health', timeout=4).status == 200 else 1)"

ENTRYPOINT ["/entrypoint.sh"]
CMD ["uvicorn", "src.api:app", "--host", "0.0.0.0", "--port", "8001", "--proxy-headers", "--forwarded-allow-ips=*"]
