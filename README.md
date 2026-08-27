# Sentinelly — Secure AI Workspace

Plataforma interna de mensajería con copiloto RAG cuya recuperación está limitada por los
permisos reales del usuario autenticado.

> The LLM never decides what the user is allowed to see. PostgreSQL decides what context can
> be retrieved; the LLM only reasons over authorized context. Authorization happens before
> generation.

Ver `docs/TRACEABILITY.md` para el estado de cada requisito y `DECISIONS.md` para el registro
de decisiones de diseño (formato Decision/Context/Why/Alternatives/Trade-off).

## Stack

- Frontend: React + TypeScript (Vite)
- Backend: FastAPI + Python, Clean Architecture
- Database: PostgreSQL 16 + pgvector
- Auth: JWT + refresh tokens (rotación + reuse detection)
- LLM: DeepSeek (compatible con el SDK de OpenAI) — `backend/domain/ports.py::LLMProvider`
- Embeddings: fastembed local, multilingüe, sin API key — `EmbeddingProvider`
- Testing: Pytest contra PostgreSQL real (sin mocks)
- Infra: Docker Compose

## Cómo correr el proyecto (máquina limpia)

Requisitos: Docker + Docker Compose.

```bash
cp .env.example .env
```

Completa en `.env`:
- `POSTGRES_PASSWORD` y `RW_APP_PASSWORD` — cualquier password, son para el Postgres local.
- `JWT_SECRET` — cualquier string largo aleatorio.
- `DEEPSEEK_API_KEY` — tu API key de [DeepSeek](https://platform.deepseek.com) (necesaria
  para el copiloto; el resto de la app funciona sin ella).

Luego:

```bash
docker compose up -d          # levanta PostgreSQL + Backend + Frontend
bash scripts/migrate.sh       # aplica DDL, funciones, policies, triggers, vistas (idempotente)
bash scripts/seed.sh          # carga el corpus de demo (2 usuarios, canal compartido + privado)
```

Abre **http://localhost:5173**. Usuarios de demo (misma contraseña `DemoPass123!`):

| Email | Ve |
|---|---|
| `alice@sentinel.dev` | solo `#general` |
| `bob@sentinel.dev` | `#general` y `#leadership-private` |

El primer arranque del backend tarda de 20s a ~1-2 min de más (varía con la red) mientras
descarga el modelo local de embeddings (~220MB, se cachea en el volumen del contenedor; no
vuelve a pasar en reinicios posteriores). Backend en `http://localhost:8000/docs`
(OpenAPI/Swagger autogenerado por FastAPI). `scripts/migrate.sh`/`seed.sh` no dependen de que
el backend termine de arrancar — hablan directo con Postgres.

## Documentación de API

`docs/api/openapi.json` — spec OpenAPI 3.1 exportada (importable en Swagger Editor o Postman,
no requiere el backend corriendo para consultarla). `docs/api/README.md` explica cómo
regenerarla y documenta los 2 endpoints WebSocket (`/ws/channels/{channel_id}`, `/ws/presence`)
que el estándar OpenAPI no cubre.

## Cómo correr en desarrollo (sin Docker para backend/frontend)

```bash
docker compose up -d postgres          # solo la base
bash scripts/migrate.sh && bash scripts/seed.sh

# Backend
python -m venv .venv && source .venv/Scripts/activate   # Windows Git Bash
pip install -r backend/requirements.txt
uvicorn backend.presentation.api:app --reload --port 8000

# Frontend (otra terminal)
cd frontend && cp .env.example .env && npm install && npm run dev

# Tests
pytest tests/ -v
```

## Estructura

```text
backend/       Clean Architecture: domain / application / infrastructure / presentation
frontend/      React + TypeScript (3 zonas: canales+perfil, conversación, copiloto)
database/      migrations, functions, views, policies, triggers, seeds
docs/          ERD, análisis de negocio, matriz de trazabilidad
tests/         Pytest contra PostgreSQL real
scripts/       migrate.sh / seed.sh
prompts/       system prompt versionado del copiloto
```
