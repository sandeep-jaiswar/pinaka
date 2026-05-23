from dagster import Definitions, asset


@asset
def ingestion_healthcheck() -> dict:
    return {"status": "ok", "service": "pinaka-ingestion"}


defs = Definitions(assets=[ingestion_healthcheck])
