# Normalización — Raw → 1FN → 2FN → 3FN

Este documento explica, paso a paso, qué dependencia funcional se elimina en cada forma normal
hasta llegar al esquema final de 7 tablas (`docs/erd/erd.mmd`, `docs/erd/seed.json`).

---

## Raw (sin normalizar)

Si se modelara todo como una única tabla plana de "log de mensajes", tal como podría llegar de
una fuente externa o de un primer borrador sin diseño relacional:

```text
message_id, message_content, message_status, message_created_at,
sender_id, sender_email, sender_full_name, sender_role_title,
channel_id, channel_name, channel_is_private,
history_entries[]   -- lista repetida: {previous_content, previous_status, changed_by, changed_at}
embedding_status
```

Problemas evidentes: `history_entries` es un grupo repetido (una lista dentro de una celda), y
hay atributos que describen al `sender` o al `channel`, no al `message` en sí.

---

## 1FN — eliminar grupos repetidos, valores atómicos

**Dependencia eliminada:** la multivaluada. `history_entries` no es un valor atómico — es una
lista de eventos de auditoría distintos por mensaje.

Se extrae a su propia tabla, una fila por evento:

```text
message_history(message_id, previous_content, previous_status, changed_by, changed_at)
```

La tabla raíz queda con una fila por mensaje, todos los valores atómicos:

```text
message(message_id, message_content, message_status, message_created_at,
        sender_id, sender_email, sender_full_name, sender_role_title,
        channel_id, channel_name, channel_is_private, embedding_status)
```

Esto ya es 1FN, pero todavía mezcla hechos sobre el mensaje, el remitente y el canal en una
sola fila.

---

## 2FN — eliminar dependencias parciales de una clave compuesta

La 2FN solo es relevante cuando la clave primaria es compuesta. Eso ocurre en la relación de
membresía, que en el raw original estaría implícita como:

```text
channel_membership(channel_id, user_id, channel_name, channel_is_private,
                    user_email, user_full_name, role)
```

con clave primaria compuesta `(channel_id, user_id)`.

**Dependencia eliminada:** parcial. `channel_name` y `channel_is_private` dependen solo de
`channel_id` (no de la clave completa); `user_email` y `user_full_name` dependen solo de
`user_id`. Ninguno de los dos depende de `(channel_id, user_id)` en conjunto — eso es una
dependencia parcial, prohibida en 2FN.

Se separan los atributos que dependen de una sola parte de la clave:

```text
rw_channels(channel_id PK, name, is_private, ...)
rw_users(user_id PK, email, full_name, ...)
rw_channel_members(channel_id FK, user_id FK, role, joined_at)   -- solo lo que depende de AMBAS
```

`role` y `joined_at` sí describen la membresía en sí (dependen de la pareja completa
canal+usuario), así que se quedan en `rw_channel_members`.

---

## 3FN — eliminar dependencias transitivas

**Dependencia eliminada:** transitiva. En la tabla `message` post-1FN:

```text
message_id → sender_id → sender_email, sender_full_name, sender_role_title
message_id → channel_id → channel_name, channel_is_private
```

`sender_email` no depende directamente de `message_id`: depende de `sender_id`, que a su vez
depende de `message_id`. Es una dependencia transitiva (vía `sender_id`), igual que
`channel_name` vía `channel_id`. Viola 3FN.

Se elimina dejando en `rw_messages` solo lo que depende directamente de `message_id`, y las
referencias (FK) a las tablas que ya tienen esos atributos como su propia clave:

```text
rw_messages(id PK, channel_id FK, sender_id FK, content, message_status,
            search_vector, created_at, updated_at)
```

`sender_email`/`sender_full_name`/`sender_role_title` ya viven en `rw_users` (desde 2FN);
`channel_name`/`channel_is_private` ya viven en `rw_channels`. No se duplican.

El mismo razonamiento aplica a `rw_message_history` (los datos de `changed_by` viven en
`rw_users`, no se repiten aquí) y a `rw_message_embeddings` (separada porque `embedding_status`
depende de un pipeline asíncrono distinto al ciclo de vida del mensaje, Fase 10 —
`message_id → embedding_status` es una dependencia real pero de una entidad conceptualmente
distinta: el estado de un job asíncrono, no un atributo intrínseco del mensaje).

---

## Resultado (3FN)

```text
rw_users              — id → email, password_hash, full_name, role_title, ...
rw_channels            — id → name, is_private, created_by, ...
rw_channel_members     — (channel_id, user_id) → role, joined_at
rw_messages             — id → channel_id, sender_id, content, message_status, ...
rw_message_history      — id → message_id, previous_content, previous_status, changed_by, ...
rw_message_embeddings   — message_id → embedding, status
rw_refresh_tokens       — id → user_id, token_hash, expires_at, revoked_at, ...
```

Cada tabla no clave depende de la clave, de toda la clave y de nada más que la clave — 3FN
cumplida. No se persiguió 4FN/5FN/BCNF: el modelo no tiene dependencias multivaluadas
adicionales relevantes para el alcance de esta prueba (ver `DECISIONS.md`, filosofía de
recorte del plan).
