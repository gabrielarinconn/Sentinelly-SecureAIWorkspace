# Business Analysis

## Actores

| Actor | Descripción |
|---|---|
| **User** | Persona autenticada que interactúa con el sistema. Toda acción se ejecuta en su nombre, identificada exclusivamente por el `user_id` del JWT verificado. |
| **Channel Owner** | Miembro de un canal con privilegios de administración sobre ese canal (gestión de miembros). Todo owner es también member — no es un rol separado a nivel de usuario, sino un valor de `role` en `rw_channel_members`. |
| **Channel Member** | Usuario perteneciente a un canal. Puede leer y enviar mensajes, editar/eliminar los propios. |
| **AI Copilot** | No es un actor humano. Actúa siempre en nombre del usuario autenticado, nunca con permisos propios ni elevados — su retrieval está sujeto a las mismas políticas RLS que cualquier consulta del usuario. |

No se define un rol `admin` en esta fase: el plan es explícito en que no deben crearse roles
sin una funcionalidad real que los requiera (ver Fase 5 de `sentinel-plan-final.md`). Si surge
una necesidad concreta más adelante, se documentará en `DECISIONS.md`.

## Entidades

| Entidad | Propósito |
|---|---|
| `rw_users` | Identidad, credenciales (hash), nombre y cargo del usuario. |
| `rw_channels` | Canales de conversación (públicos/privados). |
| `rw_channel_members` | Relación N:N user↔channel, con `role` (`owner`/`member`). Es la tabla que RLS usa para decidir membresía. |
| `rw_messages` | Mensajes enviados a un canal. Nunca se borran físicamente — `message_status` (`active`/`edited`/`deleted`). |
| `rw_message_history` | Auditoría: estado previo de un mensaje antes de cada edición/eliminación, poblada por trigger `BEFORE UPDATE`. |
| `rw_message_embeddings` | Vector (pgvector) por mensaje para retrieval del copiloto, con `status` (`pending`/`completed`/`failed`) para el pipeline asíncrono. |
| `rw_refresh_tokens` | Refresh tokens hasheados, con rotación y revocación, para detección de reuse. |

## Reglas de negocio

Cada regla tiene un dueño técnico explícito para saber, antes de tocar SQL, quién es
responsable de hacerla cumplir. "RLS" = política de PostgreSQL (frontera final, incluso si el
backend tiene un bug). "Backend" = capa de aplicación (casos de uso, middleware, DB functions
invocadas por el backend).

| ID | Regla | Dueño técnico | Por qué |
|---|---|---|---|
| R01 | A user can belong to multiple channels. | Backend (esquema) | Modelado como N:N en `rw_channel_members`; no requiere enforcement adicional, es estructural. |
| R02 | A channel can have multiple members. | Backend (esquema) | Misma tabla, misma razón — cardinalidad N:N. |
| R03 | Only channel members can read channel messages. | RLS | Es la regla central del proyecto; debe sobrevivir aunque el backend falle o sea bypaseado. Policy sobre `rw_messages` contra `rw_channel_members`. |
| R04 | Only authorized users can search messages. | RLS + Backend | `search_messages()` ejecuta bajo el actor real (`SET LOCAL app.current_user_id`); RLS filtra las filas, el backend nunca reconstruye ni relaja ese filtro. |
| R05 | The AI can only retrieve messages from channels accessible to the authenticated user. | RLS | `retrieve_ai_context()` hereda RLS del invoker — el pipeline es `JWT → app.current_user_id → RLS → pgvector`, nunca al revés. |
| R06 | Messages cannot be physically deleted. | Backend + RLS/DB | Backend nunca emite `DELETE FROM rw_messages` (solo `UPDATE message_status='deleted'`); a nivel DB, el rol de aplicación no necesita (ni debería tener) privilegio `DELETE` sobre esa tabla. |
| R07 | Previous message states must be preserved. | DB (trigger) | Trigger `BEFORE UPDATE` en `rw_messages` copia `OLD` a `rw_message_history`. No depende de que el backend "se acuerde" de auditar — es automático a nivel de base de datos. |
| R08 | The authenticated user is obtained from the JWT. | Backend | Middleware de auth extrae y verifica `user_id` del JWT firmado; nunca se acepta `user_id` del body del request. |
| R09 | Database authorization is the final security boundary. | RLS | Principio arquitectónico del proyecto: aunque backend/frontend fallen, PostgreSQL sigue negando acceso no autorizado. |
| R10 | Chat content is untrusted data. | Backend (capa de aplicación del copiloto) | El contenido de mensajes se trata siempre como dato, nunca como instrucción para el LLM — se aplica en el system prompt (`prompts/`) y en cómo se construye el contexto, no es una regla de base de datos. |

## DoD Fase 1

- ✅ Actores definidos, sin roles sin función real (`admin` explícitamente descartado por ahora).
- ✅ Entidades listadas con su propósito.
- ✅ Las 10 reglas de negocio (R01–R10) están escritas.
- ✅ Cada regla tiene un dueño técnico claro (RLS, Backend, o ambos) antes de tocar SQL.
