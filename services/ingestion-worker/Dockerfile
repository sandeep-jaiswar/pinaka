FROM python:3.11-slim

WORKDIR /app
COPY services/ingestion-worker/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY services/ingestion-worker/src /app/src
ENV PYTHONPATH=/app/src

CMD ["python", "-m", "pinaka_ingestion.cli", "backfill-plan", "--dataset", "bhavcopy", "--start-date", "2026-01-01", "--end-date", "2026-01-15", "--chunk-days", "5"]
