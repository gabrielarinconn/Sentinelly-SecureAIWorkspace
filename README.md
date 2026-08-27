# Sentinelly — Secure AI Workspace

Plataforma interna de mensajería con copiloto RAG cuya recuperación está limitada por los
permisos reales del usuario autenticado.

> Authorization happens before generation.

## Estado

Proyecto en construcción. Ver `docs/TRACEABILITY.md` para el estado de cada requisito y
`DECISIONS.md` para el registro de decisiones de diseño.

## Stack

- Frontend: React + TypeScript
- Backend: FastAPI + Python
- Database: PostgreSQL 15+ + pgvector
- Auth: JWT + refresh tokens
- Testing: Pytest contra PostgreSQL real
- Infra: Docker Compose

## Cómo correr el proyecto

_Pendiente — se documentará en la Fase de Docker/despliegue._

## Estructura

```text
backend/       Clean Architecture: domain / application / infrastructure / presentation
frontend/      React + TypeScript
database/      migrations, functions, views, policies, triggers, seeds
docs/          ERD, seguridad, matriz de trazabilidad
tests/         Pytest contra PostgreSQL real
scripts/       utilidades de desarrollo/despliegue
prompts/       system prompts versionados del copiloto
docker/        configuración de contenedores
```
