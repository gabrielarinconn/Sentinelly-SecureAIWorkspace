# Traceability Matrix

Distinción: **implementado ≠ demostrado**. Un requisito solo pasa a 🟢 cuando existe evidencia
(test pasando, captura, o entrada en el video) que lo prueba.

Estado: ⬜ pendiente · 🟡 implementado/no demostrado · 🟢 demostrado

| ID  | Requisito | Implementación | Estado | Evidencia |
|-----|-----------|-----------------|--------|-----------|
| R01 | Modelo 3FN | docs/erd/normalization.md, ERD.pdf | ⬜ | |
| R02 | RLS activo (canales/mensajes) | database/policies/ | ⬜ | |
| R03 | Rol app sin BYPASSRLS | database/migrations/ | ⬜ | |
| R04 | Vista de conversaciones (security_invoker) | database/views/ | ⬜ | |
| R05 | 2 procedimientos (consulta/edición-eliminación usuarios) | database/procedures/ | ⬜ | |
| R06 | Keyset pagination (no OFFSET) | get_channel_messages() | ⬜ | |
| R07 | Search + highlighting (ts_headline) | search_messages() | ⬜ | |
| R08 | RAG autorizado en SQL | retrieve_ai_context() | ⬜ | |
| R09 | Copilot conoce nombre/cargo | JWT claims → server-side context | ⬜ | |
| R10 | Citas en respuestas del copiloto | prompts/, application/ask_copilot | ⬜ | |
| R11 | Negativas explícitas | system prompt | ⬜ | |
| R12 | Realtime (post-COMMIT) | WebSocket | ⬜ | |
| R13 | Soft delete + historial | rw_message_history + trigger | ⬜ | |
| R14 | i18n (ES/EN, sin strings hardcoded) | frontend/i18n/ | ⬜ | |
| R15 | JWT + refresh + rotation + reuse detection | auth module | ⬜ | |
| R16 | Clean Architecture (dominio sin FastAPI/driver/SDK) | backend/domain/ | ⬜ | |
| R17 | SOLID / patrón justificado | DECISIONS.md | ⬜ | |
| R18 | Test: non-member denegado | tests/ | ⬜ | |
| R19 | Test: RAG no filtra canal privado ajeno | tests/ | ⬜ | |
| R20 | Docker compose up (DB+backend+frontend) | docker-compose.yml | ⬜ | |
| R21 | Correlation ID | middleware + error envelope | ⬜ | |
| R22 | Primer commit sin lógica previa | git log | ⬜ | |
