# Traceability Matrix

Distinción: **implementado ≠ demostrado**. Un requisito solo pasa a 🟢 cuando existe evidencia
(test pasando, captura, o entrada en el video) que lo prueba.

Estado: ⬜ pendiente · 🟡 implementado/no demostrado · 🟢 demostrado

| ID  | Requisito | Implementación | Estado | Evidencia |
|-----|-----------|-----------------|--------|-----------|
| R01 | Modelo 3FN | docs/erd/normalization.md, ERD.pdf, database/migrations/ | 🟡 | DDL corre desde cero, constraints verificadas manualmente (Fase 3); falta test automatizado (Fase 20) |
| R02 | RLS activo (canales/mensajes) | database/policies/0001_channels_messages_rls.sql | 🟢 | tests/test_fase4_rls_jwt.py (member/non-member/fail-closed, 4 tests) |
| R03 | Rol app sin BYPASSRLS | database/migrations/0009_app_role.sql | 🟢 | tests/test_fase4_rls_jwt.py::test_app_role_has_no_superuser_or_bypassrls |
| R04 | Vista de conversaciones (security_invoker) | database/views/0001_user_conversations.sql | 🟢 | tests/test_fase9_conversations_procedures.py (Alice ve 1 canal, Bob ve 2, roles correctos) |
| R05 | 2 procedimientos (consulta/edición-eliminación usuarios) | database/procedures/ | 🟢 | tests/test_fase9_conversations_procedures.py (CALL + FETCH, edición/desactivación solo del propio actor) |
| R06 | Keyset pagination (no OFFSET) | database/functions/0002_get_channel_messages.sql | 🟢 | tests/test_fase8_search_history.py::test_keyset_pagination_never_uses_offset_and_pages_through_all_messages |
| R07 | Search + highlighting (ts_headline) | database/functions/0003_search_messages.sql | 🟢 | tests/test_fase8_search_history.py (highlight, RLS-scoped, query vacío rechazado) |
| R08 | RAG autorizado en SQL | database/functions/0004_retrieve_ai_context.sql | 🟢 | tests/test_fase12_secure_retrieval.py |
| R09 | Copilot conoce nombre/cargo | lookup server-side (D012), backend/application/ask_copilot.py | 🟢 | tests/test_fase18_copilot.py::test_copilot_knows_name_and_role_without_being_asked_directly + verificado en navegador |
| R10 | Citas en respuestas del copiloto | prompts/copilot_v1.txt, backend/application/ask_copilot.py | 🟢 | tests/test_fase18_copilot.py (citations por mensaje recuperado) + verificado en navegador |
| R11 | Negativas explícitas | prompts/copilot_v1.txt (regla 3) | 🟢 | tests/test_fase19_ai_security.py::test_no_authorized_context_produces_zero_citations_not_a_hallucination |
| R12 | Realtime (post-COMMIT) | backend/infrastructure/realtime.py, presentation/api.py | 🟢 | tests/test_fase7_realtime.py (6 tests: broadcast, orden commit-then-publish, non-member rechazado, token inválido rechazado) |
| R13 | Soft delete + historial | rw_message_history + database/triggers/0001_messages_audit.sql | 🟢 | tests/test_fase6_messages_audit.py (audit trail, physical DELETE blocked, deleted message immutable) |
| R14 | i18n (ES/EN, sin strings hardcoded) | frontend/src/i18n/ | 🟢 | verificado en navegador (Playwright): detección automática de idioma, selector ES/EN, responsive desktop/mobile |
| R15 | JWT + refresh + rotation + reuse detection | backend/application/{refresh_token,issue_refresh_token,logout}.py | 🟢 | tests/test_fase15_refresh_tokens.py (rotación, reuse detection revoca cadena completa, logout) |
| R16 | Clean Architecture (dominio sin FastAPI/driver/SDK) | backend/domain/, backend/application/ | 🟢 | tests/test_fase13_clean_architecture.py (chequeo estático de imports, AST) |
| R17 | SOLID / patrón justificado | DECISIONS.md (D010) | 🟢 | Strategy (providers) + Repository (persistencia), justificados con el problema real que resuelven |
| R18 | Test: non-member denegado | tests/ | 🟢 | tests/test_fase4_rls_jwt.py, tests/test_fase5_channel_acl.py, tests/test_fase6_messages_audit.py |
| R19 | Test: RAG no filtra canal privado ajeno | tests/test_fase12_secure_retrieval.py | 🟢 | non-member 0 filas del canal privado ante 3 queries distintas, incluida una que pide explícitamente ese contenido |
| R20 | Docker compose up (DB+backend+frontend) | docker-compose.yml, backend/Dockerfile, frontend/Dockerfile | 🟢 | verificado desde volumen limpio (`docker compose down -v` → `up -d` → migrate → seed → login/chat/copilot en navegador, todo cross-container) |
| R21 | Correlation ID | backend/presentation/{middleware,errors}.py | 🟢 | tests/test_fase16_api_errors_correlation.py |
| R22 | Primer commit sin lógica previa | git log | ⬜ | |
