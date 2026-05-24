FROM python:3.11-slim

WORKDIR /opt/dagster
COPY services/orchestrator-dagster/requirements.txt /opt/dagster/requirements.txt
COPY packages/python/pinaka-common /opt/dagster/packages/pinaka-common
RUN pip install --no-cache-dir -r /opt/dagster/requirements.txt && \
    pip install --no-cache-dir -e /opt/dagster/packages/pinaka-common

ENV DAGSTER_HOME=/opt/dagster/dagster_home
EXPOSE 3000

CMD ["dagster-webserver", "-h", "0.0.0.0", "-p", "3000", "-w", "/opt/dagster/dagster_home/workspace.yaml"]
