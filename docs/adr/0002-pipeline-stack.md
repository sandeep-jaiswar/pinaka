# ADR-0002: Pipeline Stack Choices

## Status
Accepted

## Context
Need an open-source heavy stack that works locally and maps cleanly to AWS.

## Decision
- Orchestration: Dagster OSS
- Lake storage: S3 API via MiniStack
- Event bus: Redpanda (Kafka API)
- Serving analytics: ClickHouse
- Transform framework: dbt-clickhouse
- Metadata state: PostgreSQL

## Why
- Dagster has first-class partition/backfill semantics.
- ClickHouse is efficient for time-series + analytical screening queries.
- Redpanda keeps streaming interfaces open without managed cloud lock-in.
- MiniStack enables low-cost AWS-compatible local development.
