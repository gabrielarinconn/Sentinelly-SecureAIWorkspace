# Security Threat Matrix

Cada fila: la amenaza, la defensa, dónde vive en el código, y qué test la demuestra.

| Amenaza | Defensa | Dónde | Evidencia |
|---|---|---|---|
| Acceso no autorizado a un canal | RLS (`rw_channels`/`rw_messages`, actor via `app.current_user_id`) | `database/policies/0001_channels_messages_rls.sql` | `tests/test_fase4_rls_jwt.py` |
| Retrieval de RAG no autorizado | RLS aplicado ANTES de la similitud vectorial — `retrieve_ai_context()` nunca ve filas fuera de lo autorizado | `database/functions/0004_retrieve_ai_context.sql` | `tests/test_fase12_secure_retrieval.py`, `tests/test_fase19_ai_security.py` |
| Prompt injection (contenido de mensaje como instrucción) | Contenido tratado como dato en el system prompt; regla explícita de "no obedecer" | `prompts/copilot_v1.txt` (regla 1) | `tests/test_fase19_ai_security.py` |
| Manipulación de JWT | Verificación de firma HMAC (`PyJWT`), `user_id` siempre de `sub`, nunca del body/query | `backend/infrastructure/jwt_service.py` | `tests/test_fase4_rls_jwt.py::test_login_issues_a_real_signed_jwt` |
| Robo/reuso de refresh token | Hash (SHA-256) en DB, rotación, reuse detection revoca toda la cadena | `backend/application/refresh_token.py`, D013 | `tests/test_fase15_refresh_tokens.py` |
| Inyección SQL | Queries parametrizadas en todo el proyecto — nunca concatenación | todo `backend/infrastructure/*_repository.py` | `tests/test_fase20_sql_injection.py` |
| Eliminación física de mensajes | Sin privilegio `DELETE` en `rw_messages` para `rw_app`; trigger de auditoría; solo `UPDATE message_status` | `database/migrations/0009_app_role.sql`, `database/triggers/0001_messages_audit.sql` | `tests/test_fase6_messages_audit.py::test_physical_delete_is_blocked_by_privileges_not_just_by_convention` |
| Inconsistencia de datos ante error a medio camino | Transacciones (`authorized_transaction`, `conn.transaction()`) — todo o nada | `backend/infrastructure/db.py` | `tests/test_fase6_messages_audit.py` (rollback en mensaje ya eliminado) |
| Falta de trazabilidad de requests | Correlation ID por request, en logs y en el envelope de error | `backend/presentation/middleware.py`, `errors.py` | `tests/test_fase16_api_errors_correlation.py` |
| Una vista que bypassea RLS silenciosamente | `security_invoker = true` explícito en `view_user_conversations` | `database/views/0001_user_conversations.sql` | `tests/test_fase9_conversations_procedures.py` |
| Impersonar a otro usuario al enviar un mensaje | RLS `WITH CHECK (sender_id = actor)` — imposible falsificar el remitente | `database/policies/0003_messages_write.sql` | `tests/test_fase6_messages_audit.py::test_cannot_send_impersonating_another_sender` |
| Editar/borrar un mensaje ajeno | RLS `USING (sender_id = actor)` en UPDATE | `database/policies/0003_messages_write.sql` | `tests/test_fase16_api_errors_correlation.py::test_non_owner_cannot_edit_or_delete_someone_elses_message` |
| Editar/desactivar la cuenta de otro usuario | El procedimiento nunca recibe un `user_id` externo — opera solo sobre `app.current_user_id` | `database/procedures/0002_edit_delete_user.sql` | `tests/test_fase9_conversations_procedures.py::test_edit_user_procedure_only_ever_touches_the_calling_actor` |
| Fuga de metadata de membresía (quién está en qué canal) | RLS también sobre `rw_channel_members`, vía función `SECURITY DEFINER` acotada | `database/policies/0002_channel_members_rls.sql`, `database/functions/0001_is_channel_member.sql` | `tests/test_fase5_channel_acl.py` |
| Filtrar contraseñas/tokens en texto plano | bcrypt (passwords), SHA-256 (refresh tokens) — nunca texto plano en DB | `backend/infrastructure/password_hasher.py`, `application/tokens.py` | seed usa `crypt(..., gen_salt('bf'))`; D013 |
| Fuga de credenciales en el repositorio | `.env` real nunca commiteado; `.mcp.json`/`.claude/` fuera de git; solo `.env.example` sin valores | `.gitignore` | — |

## Notas

- La garantía de mayor peso del proyecto es la primera fila combinada con la segunda: **toda
  autorización se decide en PostgreSQL antes de que el LLM genere una sola palabra** — ver
  `ARCHITECTURE.md` y el principio central en `CLAUDE.md`/`README.md`.
- El escenario de prompt injection (tabla, fila 3) queda para la sustentación técnica, no para
  el video de evidencia (Fase 24 del plan).
