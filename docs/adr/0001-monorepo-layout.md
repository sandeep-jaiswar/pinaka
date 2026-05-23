# ADR-0001: Adopt Monorepo Layout for Pinaka

## Status
Accepted

## Context
Pinaka will include multiple independently deployable services, shared schemas, shared pipeline logic, and infrastructure definitions.

## Decision
Adopt a monorepo with top-level folders:
- `services/` deployable units
- `packages/` shared libraries
- `infra/` Docker/Kubernetes/Terraform
- `docs/` architecture and runbooks
- `data-contracts/` schemas and contracts

## Consequences
### Positive
- atomic changes across pipeline + schema + infra
- easier onboarding and discoverability
- consistent CI patterns

### Negative
- larger CI surface over time
- requires disciplined boundaries between services
