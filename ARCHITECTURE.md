# Architecture

## Principio central

> The LLM never decides what the user is allowed to see. PostgreSQL decides what context can
> be retrieved; the LLM only reasons over authorized context. Authorization happens before
> generation.

## Capas

```text
Frontend → Backend → PostgreSQL → RLS
```

El frontend no es frontera de seguridad (`localStorage` para tokens, D011 cut #3). El backend
tampoco es la única — usa el rol `rw_app`, sin `BYPASSRLS`, para TODA consulta en tiempo de
ejecución (D002). PostgreSQL es la última barrera, y la única que realmente importa: incluso
si el backend tuviera un bug de autorización, RLS sigue negando filas no autorizadas.

## Flujo del copiloto RAG (la parte más importante del sistema)

```text
JWT verificado → user_id (nunca del body)
   → SET LOCAL app.current_user_id (D003, set_config parametrizado)
   → embedding de la pregunta (fastembed local, D007)
   → retrieve_ai_context(embedding) — SELECT normal sobre rw_messages,
     RLS ya filtra qué filas existen para este actor (D002)
   → top-K por similitud, SOLO entre lo ya autorizado
   → system prompt (prompts/copilot_v1.txt): contexto = dato, nunca instrucción
   → DeepSeek (D007) genera la respuesta
   → citas = exactamente los mensajes que estaban en el contexto (nunca lo que el LLM "dice"
     haber citado — la lista de citas es del backend, no del LLM)
```

Nunca: `todos los mensajes → similitud → filtrar permisos en Python`. Esa forma de construir
el pipeline es exactamente lo que el principio central prohíbe, y por eso
`retrieve_ai_context()` es una función SQL normal (SECURITY INVOKER) — no hay ningún punto
del pipeline donde exista "todos los mensajes" como conjunto intermedio.

## Backend — Clean Architecture

```text
backend/
├── domain/          Python puro. Entidades (dataclasses) + puertos (ABC). Sin FastAPI, sin
│                     psycopg, sin SDK de LLM/embeddings. Verificado por test estático
│                     (tests/test_fase13_clean_architecture.py, análisis de AST).
├── application/      Casos de uso delgados: Validate → Call repository/provider → Map result.
│                     Dependen solo de domain/ports, nunca de infrastructure directamente.
├── infrastructure/   Implementaciones concretas de los puertos: PsycopgXRepository,
│                     BcryptPasswordHasher, JwtTokenService, DeepSeekLLMProvider,
│                     FastEmbedProvider. Es la ÚNICA capa que importa SDKs externos.
└── presentation/     FastAPI: rutas, middleware (correlation ID, CORS), manejo de errores
                       uniforme, wiring (arma los casos de uso con sus dependencias concretas).
```

Patrones aplicados (justificados en detalle en `DECISIONS.md`, D010):

- **Strategy** — `LLMProvider`/`EmbeddingProvider`/`PasswordHasher`/`TokenService` son
  interfaces; cada una tiene una sola implementación real, intercambiable sin tocar
  `application/` ni `presentation/`.
- **Repository** — `UserRepository`/`MessageRepository`/etc. exponen operaciones de negocio
  completas (no CRUD genérico) y nunca deciden autorización por su cuenta: eso es trabajo de
  RLS, no del repositorio (D002).

## Base de datos

```text
database/
├── migrations/   DDL: tablas, constraints, roles (numeradas, aplicadas en orden)
├── functions/    SELECT-only, SECURITY INVOKER salvo un caso justificado (rw_is_channel_member,
│                  SECURITY DEFINER — D011 cut #2, rompe una recursión de RLS)
├── policies/     CREATE POLICY — quién puede hacer qué, por tabla
├── triggers/     Auditoría (rw_message_history), tsvector, embeddings pendientes
├── procedures/   Los 2 procedimientos exigidos — CALL, no SELECT (consulta/edición de usuarios)
├── views/        view_user_conversations, WITH (security_invoker = true) obligatorio
└── seeds/        Escenario de demo reproducible
```

`scripts/migrate.sh` aplica todo en orden (`migrations → functions → procedures → policies →
triggers → views`), es idempotente (tabla `schema_migrations`) y no depende de que el backend
esté corriendo — solo de `docker compose`'s servicio `postgres`.

## Realtime

WebSocket nativo de FastAPI, pub/sub en memoria, single-process (D008). Orden estricto:
`COMMIT exitoso → evento` — nunca al revés (ver `backend/presentation/api.py::send_message`).

## Frontend

Layout de 3 zonas (`frontend/src/App.tsx`): sidebar (canales + perfil), conversación (centro),
copiloto (derecha). i18n propio (sin librería, D011 cut #3) con detección automática de
idioma del navegador. Estado de entrega optimista (`pending`/`sent`/`failed`, D009) vive solo
en el cliente — nunca en la base de datos.

## Ver también

- `DECISIONS.md` — cada decisión no trivial, con el problema real que resolvió.
- `docs/security/threat-matrix.md` — amenaza por amenaza, defensa y evidencia.
- `docs/TRACEABILITY.md` — estado de cada requisito del enunciado.
- `docs/erd/` — modelo de datos, normalización 3FN.
