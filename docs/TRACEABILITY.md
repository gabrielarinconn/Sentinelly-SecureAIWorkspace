# Traceability Matrix

Distinción: **implementado ≠ demostrado**. Un requisito solo pasa a 🟢 cuando existe evidencia
(test pasando, captura, o entrada en el video) que lo prueba.

Estado: ⬜ pendiente · 🟡 implementado/no demostrado · 🟢 demostrado

| ID  | Requisito | Implementación | Estado | Evidencia |
|-----|-----------|-----------------|--------|-----------|
| R01 | Modelo 3FN | docs/erd/normalization.md, ERD.pdf, database/migrations/ | 🟡 | DDL corre desde cero, constraints verificadas manualmente (Fase 3); falta test automatizado (Fase 20) |
| R02 | RLS activo (canales/mensajes) | database/policies/0001_channels_messages_rls.sql | 🟢 | tests/test_fase4_rls_jwt.py (member/non-member/fail-closed, 4 tests) |
| R03 | Rol app sin BYPASSRLS | database/migrations/0009_app_role.sql | 🟢 | tests/test_fase4_rls_jwt.py::test_app_role_has_no_superuser_or_bypassrls |
| R04 | Vista de conversaciones (security_invoker) | database/views/ | ⬜ | |
| R05 | 2 procedimientos (consulta/edición-eliminación usuarios) | database/procedures/ | ⬜ | |
| R06 | Keyset pagination (no OFFSET) | get_channel_messages() | ⬜ | |
| R07 | Search + highlighting (ts_headline) | search_messages() | ⬜ | |
| R08 | RAG autorizado en SQL | retrieve_ai_context() | ⬜ | |
| R09 | Copilot conoce nombre/cargo | JWT claims → server-side context | ⬜ | |
| R10 | Citas en respuestas del copiloto | prompts/, application/ask_copilot | ⬜ | |
| R11 | Negativas explícitas | system prompt | ⬜ | |
| R12 | Realtime (post-COMMIT) | WebSocket | ⬜ | |
| R13 | Soft delete + historial | rw_message_history + database/triggers/0001_messages_audit.sql | 🟢 | tests/test_fase6_messages_audit.py (audit trail, physical DELETE blocked, deleted message immutable) |
| R14 | i18n (ES/EN, sin strings hardcoded) | frontend/i18n/ | ⬜ | |
| R15 | JWT + refresh + rotation + reuse detection | auth module | ⬜ | |
| R16 | Clean Architecture (dominio sin FastAPI/driver/SDK) | backend/domain/ | 🟡 | verificado manualmente (grep de imports); falta test automatizado (Fase 13/20) |
| R17 | SOLID / patrón justificado | DECISIONS.md | ⬜ | |
| R18 | Test: non-member denegado | tests/ | 🟢 | tests/test_fase4_rls_jwt.py, tests/test_fase5_channel_acl.py, tests/test_fase6_messages_audit.py |
| R19 | Test: RAG no filtra canal privado ajeno | tests/ | ⬜ | |
| R20 | Docker compose up (DB+backend+frontend) | docker-compose.yml | ⬜ | |
| R21 | Correlation ID | middleware + error envelope | ⬜ | |
| R22 | Primer commit sin lógica previa | git log | ⬜ | |
