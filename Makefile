SHELL := /bin/bash

DOCKER_COMPOSE := COMPOSE_PROJECT_NAME=pinaka docker compose -f infra/docker/docker-compose.yml --env-file infra/docker/.env

.PHONY: up down logs ps health ministack-init backfill-plan backfill-run ingestion-image ingest-bhavcopy-eq ingest-bhavcopy-eq-range

up:
	$(DOCKER_COMPOSE) up -d --build

down:
	$(DOCKER_COMPOSE) down

logs:
	$(DOCKER_COMPOSE) logs -f --tail=200

ps:
	$(DOCKER_COMPOSE) ps

health:
	curl -s http://localhost:4566/_ministack/health | sed 's/,/\n/g' || true

ministack-init:
	bash scripts/create_ministack_resources.sh

backfill-plan:
	PYTHONPATH=services/ingestion-worker/src python3 -m pinaka_ingestion.cli backfill-plan --start-date 2015-01-01 --end-date 2026-01-01 --chunk-days 30

backfill-run:
	bash scripts/run_backfill.sh

ingestion-image:
	docker build -t pinaka-ingestion-worker -f services/ingestion-worker/Dockerfile .

ingest-bhavcopy-eq: ingestion-image
	docker run --rm --network pinaka_default pinaka-ingestion-worker python -m pinaka_ingestion.cli ingest-bhavcopy-eq --trade-date $${TRADE_DATE:-2026-05-22} --bucket pinaka-raw --endpoint-url http://ministack:4566 --region ap-south-1

ingest-bhavcopy-eq-range: ingestion-image
	docker run --rm --network pinaka_default pinaka-ingestion-worker python -m pinaka_ingestion.cli ingest-bhavcopy-eq-range --start-date $${START_DATE:-2026-05-20} --end-date $${END_DATE:-2026-05-22} --chunk-days $${CHUNK_DAYS:-5} --bucket pinaka-raw --endpoint-url http://ministack:4566 --region ap-south-1 --continue-on-error
