# Decisions

Registro de decisiones de diseño no triviales y recortes de alcance. Formato por entrada:
`Decision / Context / Why / Alternatives / Trade-off`.

---

## D001 — UUID vs serial

**Decision:** todas las PK son `uuid` (generadas en la aplicación o con `gen_random_uuid()`),
no `serial`/`bigserial`.

**Context:** el `user_id` viaja en el JWT y se expone en la URL/respuestas de la API
(`/channels/{id}/messages`, `/messages/{id}`, etc.).

**Why:** un ID secuencial (`serial`) permite enumeración — un atacante autenticado puede
iterar `channel_id=1,2,3...` y sondear la existencia de canales/mensajes ajenos aunque RLS
bloquee el contenido, filtrando metadata (existencia, volumen de datos). UUID v4 no es
adivinable. También evita colisiones si en el futuro se necesita generar IDs fuera de una
única secuencia centralizada (p. ej. en el cliente, en tests, en un seed reproducible).

**Alternatives:** `bigserial` con verificación de acceso siempre antes de exponer cualquier
dato (mitiga pero no elimina el problema de enumeración); `serial` + UUID público separado
(complejidad extra sin beneficio real para el alcance de esta prueba).

**Trade-off:** UUID ocupa más espacio en disco/índices que un entero (16 bytes vs 4-8), y no
tiene orden natural de inserción — por eso la keyset pagination (D005) usa `(created_at, id)`
como cursor compuesto, no solo `id`.

## D002 — PostgreSQL como security boundary

_Pending._

## D003 — RLS strategy

_Pending._

## D004 — Soft delete

_Pending._

## D005 — Keyset pagination

_Pending._

## D006 — Async embeddings (trigger híbrido)

_Pending._

## D007 — LLMProvider abstraction (interfaz mínima, un proveedor real)

_Pending._

## D008 — Realtime approach (WebSocket single-process; sin fallback a polling salvo recorte documentado)

_Pending._

## D009 — message_status vs delivery_status (dominio vs UI)

_Pending._

## D010 — Patrón de diseño aplicado y por qué

_Pending._

## D011 — Scope cuts

_Pending._

## D012 — Origen de nombre/cargo del usuario en el copiloto (JWT claims vs lookup server-side)

_Pending._
