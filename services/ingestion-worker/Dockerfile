FROM python:3.11-slim

WORKDIR /app
COPY services/ingestion-worker/requirements.txt /app/requirements.txt
COPY packages/python/pinaka-common /app/packages/pinaka-common
RUN pip install --no-cache-dir -r /app/requirements.txt && \
    pip install --no-cache-dir -e /app/packages/pinaka-common

COPY services/ingestion-worker/src /app/src
ENV PYTHONPATH=/app/src

CMD ["python", "-m", "pinaka_ingestion.cli", "backfill-plan", "--dataset", "bhavcopy_eq", "--start-date", "2026-01-01", "--end-date", "2026-01-15", "--chunk-days", "5"]
