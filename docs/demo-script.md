# Guion de demo (Fase 24)

Dos entregables distintos — no mezclar:

## (a) Sustentación técnica

Uso libre de tiempo, profundidad técnica. Aquí SÍ cabe el escenario de prompt injection
(`docs/security/threat-matrix.md`, fila 3; `tests/test_fase19_ai_security.py`). Preguntas que
seguro van a caer y dónde está la respuesta:

- *"¿De dónde saca el copiloto el nombre/cargo del usuario?"* → D012, lookup server-side,
  `backend/application/ask_copilot.py`.
- *"¿Por qué `retrieve_ai_context()` es segura aunque el LLM sea malicioso?"* → RLS se aplica
  en el `SELECT` antes de que exista ningún prompt — `ARCHITECTURE.md`, sección RAG.
- *"¿Por qué esta función es `SECURITY DEFINER`?"* → D011 cut #2, única excepción, justificada
  (rompe una recursión de RLS, expone solo un booleano).
- *"¿Cómo se prueba esto?"* → sin mocks, contra PostgreSQL real y llamadas reales a DeepSeek
  (`tests/test_fase18_copilot.py`, `test_fase19_ai_security.py`).

## (b) Video de evidencia — máx. 5 min, pitch comercial, sin jerga técnica

**No incluir el escenario de prompt injection acá** — queda para la sustentación.

### Guion (usuarios: alice@sentinel.dev / bob@sentinel.dev, password `DemoPass123!`)

1. **Login** (10s) — entrar como Bob. Mostrar que ve `#general` y `#leadership-private`.
2. **Enviar un mensaje** (15s) — escribir en `#general`, mostrar el estado optimista
   ("Sending..." → confirmado) y — con una segunda pestaña logueada como Alice — que el
   mensaje aparece en tiempo real sin refrescar.
3. **Buscar** (15s) — buscar "budget" en la barra de búsqueda, mostrar el resaltado amarillo
   en los resultados.
4. **Copiloto — pregunta autorizada** (30s) — "¿Qué se dijo sobre el budget?" → respuesta con
   citas numeradas, mostrar el contador "Sources cited: N".
5. **Copiloto — identidad** (15s) — "¿Quién soy?" → responde con nombre y cargo correctos sin
   que se le haya dicho.
6. **Cambiar a Alice, negativa correcta** (20s) — loguear como Alice, preguntarle al copiloto
   por el canal privado → debe admitir que no tiene contexto autorizado, no debe inventar ni
   filtrar nada del canal de Bob.
7. **Cierre** (10s) — mencionar Docker (`docker compose up` levanta todo), tests contra
   PostgreSQL real (no mocks), y el principio central: la autorización la decide la base de
   datos, no el LLM.

Todo el golden path está respaldado por tests automatizados reales, no solo por la coreografía
manual del video:

- Paso 2 (realtime) → `tests/test_fase7_realtime.py`
- Paso 3 (búsqueda) → `tests/test_fase8_search_history.py`
- Pasos 4-5 (copiloto autorizado + identidad) → `tests/test_fase18_copilot.py`
- Paso 6 (negativa) → `tests/test_fase19_ai_security.py`

## Capturas ya generadas durante el desarrollo (evidencia de respaldo)

Ver mensaje del asistente — se enviaron como archivos adjuntos: login, layout de 3 zonas con
canal abierto, búsqueda con highlighting, canal privado, responsive mobile, y el copiloto
respondiendo con citas — todas contra el stack real (Postgres + backend + frontend,
dockerizado en la verificación final de la Fase 21).
