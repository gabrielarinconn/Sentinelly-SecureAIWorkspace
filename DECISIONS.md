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

**Decision:** existen dos roles de PostgreSQL distintos y con propósitos que nunca se
mezclan: `sentinel_app` (superusuario del contenedor, solo para migrar/seedear/inspeccionar
vía MCP) y `rw_app` (sin `SUPERUSER`, sin `BYPASSRLS`, es el único rol que el backend usa en
tiempo de ejecución). `RW_APP_DATABASE_URL` ≠ `DATABASE_URL`.

**Context:** el principio central del proyecto es "authorization happens before generation" —
PostgreSQL decide qué contexto es visible, no el backend ni el LLM.

**Why:** si el backend corriera con el mismo rol usado para migrar (superusuario), RLS sería
cosmético — un bug en el backend, o el LLM manipulando parámetros, podría leer cualquier fila
sin que ninguna política lo impida. Separar los roles hace que la autorización sea real incluso
si la capa de aplicación falla por completo (R09).

**Alternatives:** un solo rol con `BYPASSRLS` y "confiar" en que el backend siempre filtra en
Python (descartado explícitamente por el plan — es exactamente el antipatrón que el principio
central prohíbe: `all messages → vector search → filter permissions in Python`).

**Trade-off:** dos connection strings que mantener sincronizadas (`.env`), y cualquier
operación administrativa nueva (agregar una tabla, un índice) requiere el rol admin — el
backend nunca puede auto-migrarse ni auto-otorgarse permisos, lo cual es intencional.

## D003 — RLS strategy

**Decision:** el actor se fija por transacción con `SELECT set_config('app.current_user_id',
'<uuid>', true)` (equivalente parametrizable de `SET LOCAL`), y las políticas usan
`current_setting('app.current_user_id', true)` con el flag `missing_ok=true` — si nunca se
fija, la comparación da `NULL` y la política deniega (fail-closed), no lanza error.

**Context:** `psycopg` (como la mayoría de drivers) no permite parámetros bindeados dentro de
`SET`/`SET LOCAL` — es una limitación del protocolo, no del driver. Se necesitaba una forma
parametrizada de fijar el actor sin concatenar el UUID como texto en el SQL (eso sería
reintroducir el riesgo de inyección que las queries parametrizadas evitan en todo lo demás).

**Why:** `set_config(name, value, is_local)` es una función normal — acepta un parámetro
bindeado (`%s`) igual que cualquier otra consulta, así que el UUID nunca se concatena en el
texto del SQL. `is_local = true` reproduce el comportamiento de `SET LOCAL`: el valor solo
vive dentro de la transacción actual y desaparece al hacer COMMIT/ROLLBACK — no puede "filtrar"
a la siguiente request si la conexión se reutiliza desde un pool.

**Alternatives:** interpolar el UUID directamente en un `SET LOCAL app.current_user_id = '...'`
con f-string (descartado — es concatenación de SQL, prohibida explícitamente); una función
`SECURITY DEFINER` que reciba el JWT completo y lo valide dentro de Postgres (más complejo,
duplica la verificación de firma que ya hace el backend con la misma librería que emite el
token).

**Trade-off:** cada transacción autorizada paga el costo de una llamada extra a
`set_config()` antes de la query real — irrelevante en la práctica frente al costo de la
propia conexión/red.

## D004 — Soft delete

**Decision:** ningún `DELETE` físico sobre `rw_messages` ni sobre `rw_users`. Los mensajes
usan `message_status` (`active`/`edited`/`deleted`); los usuarios usan `is_active`.

**Context:** el plan lo exige explícitamente para mensajes ("nunca `DELETE FROM
rw_messages`"). La segunda de las dos stored procedures obligatorias (Fase 9) es "edición y
eliminación de usuarios" — había que decidir si esa "eliminación" es física o lógica.

**Why:** físicamente borrar un usuario que ya envió mensajes rompería la integridad
referencial de `rw_messages.sender_id` y `rw_message_history.changed_by` (accountability de
auditoría, R07), o forzaría un `ON DELETE CASCADE` que borraría en cascada la conversación —
justo lo que R06/R07 prohíben. Se optó por tratar la "eliminación de usuarios" como
desactivación (`is_active = false`), consistente con el mismo patrón que mensajes.

**Alternatives:** `DELETE` real con `ON DELETE SET NULL` en `sender_id` (perdería quién envió
cada mensaje, inaceptable para auditoría); anonimizar campos en vez de un flag `is_active`
(más complejo, sin beneficio adicional para el alcance de la prueba).

**Trade-off:** un email "liberado" al desactivar un usuario podría ser reclamado por otra
persona — se acepta porque el índice único parcial (`rw_users_email_active_uk`, Fase 3) solo
exige unicidad entre usuarios activos, y es el comportamiento esperado en un sistema real
(alguien se va, el email queda libre). A nivel de esquema, ambas tablas quedan reforzadas con
`ON DELETE RESTRICT` desde `rw_messages`/`rw_message_history` hacia `rw_users`, para que un
intento accidental de `DELETE FROM rw_users` falle en vez de cascadear silenciosamente.

## D005 — Keyset pagination

**Decision:** toda paginación de mensajes usa cursor `(created_at, id)` + `limit`, nunca
`OFFSET`.

**Context:** requisito explícito del plan ("nunca paginación con OFFSET"); aplica a
`get_channel_messages()` y `search_messages()` (Fases 8 y 11).

**Why:** `OFFSET N` degrada linealmente con `N` (Postgres igual escanea y descarta las
primeras `N` filas) y es inestable si llegan mensajes nuevos entre páginas (filas que se
desplazan, duplicados o saltos). Keyset (`WHERE (created_at, id) < (cursor_ts, cursor_id)
ORDER BY created_at DESC, id DESC LIMIT n`) usa el índice directamente y es estable ante
inserciones concurrentes.

**Alternatives:** `OFFSET`/`LIMIT` (descartado, prohibido explícitamente); cursor solo por
`id` (descartado — con UUID v4 el orden de `id` no coincide con el orden de inserción, D001).

**Trade-off:** no se puede saltar directamente a "la página 5" — solo avanzar/retroceder
desde un cursor conocido. Aceptable: el frontend (Fase 17) es scroll infinito, no paginación
numerada.

## D006 — Async embeddings (trigger híbrido)

**Decision:** trigger `AFTER INSERT/UPDATE OF content` marca `rw_message_embeddings.status =
'pending'` (+ `pg_notify`, opcional/no consumido todavía) — nunca llama a un proveedor de
embeddings desde SQL. Un worker Python (`process_pending_embeddings()`) hace polling y
convierte `pending → completed|failed` fuera de la transacción original.

**Context:** llamar a una API externa desde un trigger bloquearía la transacción del INSERT
del mensaje hasta que esa API respondiera — inaceptable para una operación que debe sentirse
instantánea (enviar un mensaje).

**Why:** el trigger es rápido y determinístico (una fila más, sin I/O de red); el trabajo
lento y no determinístico (llamar a un LLM/embedding provider) vive en el backend, donde
puede reintentarse, tener timeout, y fallar sin arrastrar la transacción del mensaje consigo.

**Decisión adicional no anticipada (descubierta al probar):** el worker usa
`get_admin_connection()` (rol superusuario), no `rw_app`. Es un proceso de sistema sin actor
humano — necesita ver mensajes pendientes de **todos** los canales para vectorizarlos, y
`rw_app` sin `SET LOCAL app.current_user_id` fijado recibe 0 filas de `rw_messages` por RLS
(fail-closed), no un error, así que el bug pasó silencioso hasta que un test lo detectó. Esto
no reintroduce el problema que RLS resuelve: el vector queda en la tabla, pero nadie lo *lee*
con significado hasta `retrieve_ai_context()` (Fase 12), que sí corre bajo RLS con el actor
real — la autorización sigue pasando antes de que el LLM vea nada.

**Alternatives:** `LISTEN/NOTIFY` con un consumidor persistente en vez de polling (más
"reactivo", pero requiere mantener una conexión de larga duración y manejar reconexión —
complejidad no justificada para el alcance de esta prueba); llamar al proveedor sincrónicamente
dentro de la misma request HTTP que crea el mensaje (descartado — el usuario esperaría a que
termine el embedding para ver su propio mensaje "enviado").

**Trade-off:** hay una ventana (hasta el siguiente ciclo del worker) donde un mensaje recién
enviado todavía no es recuperable por el copiloto — aceptable, el copiloto no es tiempo real
en el mismo sentido que los mensajes.

## D007 — LLMProvider abstraction (interfaz mínima, un proveedor real)

**Decision:** dos interfaces mínimas en `domain/ports.py` (`LLMProvider.complete()`,
`EmbeddingProvider.embed()`), cada una con **una** implementación real detrás:
`DeepSeekLLMProvider` (chat, vía el SDK de OpenAI apuntado a `api.deepseek.com` — DeepSeek es
compatible con ese formato, así que no hace falta un SDK propio) y `FastEmbedProvider`
(embeddings, local, `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`, sin API
key ni red).

**Context:** el usuario paga DeepSeek y quería reusar esa cuenta; DeepSeek no ofrece API de
embeddings (verificado contra su documentación oficial), así que el LLM y los embeddings
terminaron siendo dos proveedores *reales* distintos detrás de dos interfaces distintas — no
un único "proveedor" multiproducto.

**Why:** cada interfaz sigue teniendo exactamente una implementación real, que es la regla
que pide el plan ("interfaz pequeña, un solo proveedor real detrás") — tener dos interfaces
en vez de una no es sobre-abstracción, son dos capacidades genuinamente distintas (generar
texto vs. generar vectores) que ya existían como conceptos separados desde el diseño original
(Fase 10 ya tenía `EmbeddingProvider` antes de que `LLMProvider` se implementara).

**Alternatives:** OpenAI para ambos (un solo proveedor, pero requiere una segunda cuenta/API
key que el usuario no tenía — ver conversación de la Fase 18); forzar a DeepSeek a hacer
embeddings de alguna forma (no existe ese endpoint, no es una opción real).

**Trade-off:** el proveedor de embeddings corre local (CPU, ~220MB de modelo cacheado en
disco) en vez de ser una llamada de red — más lento en frío (~3s la primera vez que se
instancia el proceso) pero sin costo y sin key adicional; ver también D006 (por qué el
worker ya corre en segundo plano, así que este costo nunca lo paga una request de usuario).

## D008 — Realtime approach (WebSocket single-process; sin fallback a polling salvo recorte documentado)

**Decision:** WebSocket nativo de FastAPI, con un broadcaster pub/sub en memoria
(`backend/infrastructure/realtime.py`) — un `dict[channel_id, set[asyncio.Queue]]` — dentro
del mismo proceso que sirve la API. Sin Redis/pub-sub externo, sin polling.

**Context:** el plan exige realtime como criterio de aceptación, con orden estricto
`request → DB transaction → COMMIT exitoso → evento realtime → clientes conectados`, y
prohíbe explícitamente sustituirlo por polling salvo recorte documentado.

**Why:** un solo proceso de backend es suficiente para el alcance de esta prueba (el plan lo
dice explícitamente: "single-process, suficiente para el assessment"). El endpoint
`POST /channels/{id}/messages` es `async def`; el trabajo de DB corre en threadpool
(`run_in_threadpool`) y el `broadcaster.publish(...)` se llama **después** de que esa llamada
retorna — es decir, después de que `authorized_transaction` ya hizo `COMMIT`. Nunca antes.

**Alternatives:** Redis Pub/Sub o Postgres `LISTEN/NOTIFY` (correctos para multi-proceso/
multi-instancia, pero una infraestructura adicional que el alcance de esta prueba no
justifica); polling (prohibido explícitamente por el plan salvo recorte documentado — no
aplica aquí, WebSocket funcionó sin necesidad de recortar nada).

**Trade-off:** si el backend corriera en más de un proceso/worker, un cliente conectado al
proceso A nunca vería un mensaje publicado desde el proceso B — el broadcaster en memoria no
escala horizontalmente. Aceptable para el alcance de la prueba; documentado explícitamente
para que quede claro en la sustentación por qué no es la arquitectura de producción.

## D009 — message_status vs delivery_status (dominio vs UI)

**Decision:** `message_status` (`active`/`edited`/`deleted`) es la única columna persistida en
`rw_messages` — es el ciclo de vida lógico del mensaje, gobernado por el trigger de auditoría
(Fase 6). `delivery_status` (`pending`/`sent`/`failed`) **no existe como columna**: es estado
optimista del frontend (Fase 17) mientras un mensaje viaja al servidor.

**Context:** son dos conceptos que suenan parecidos y es fácil colapsarlos en una sola
columna por error.

**Why:** una vez el `INSERT` hace `COMMIT`, el mensaje ya es "enviado" por definición — no
hay un estado intermedio de "enviando" que tenga sentido persistir en la base de datos, ese
estado solo existe en la UI mientras la request está en vuelo. Mezclarlos crearía una columna
que necesitaría reflejar tanto el ciclo de vida del dato (permanente, auditado) como el
estado transitorio de una request HTTP (efímero, por-cliente) — dos cosas con dueños y
tiempos de vida distintos.

**Alternatives:** una sola columna `status` con valores `pending/sent/active/edited/deleted`
(descartado — mezclaría estado de red con estado de dominio, y "pending" nunca debería poder
llegar a persistirse porque significa que el INSERT ni siquiera pasó).

**Trade-off:** el frontend necesita su propio estado local (optimistic UI) para `pending` y
`failed`, ya que la base de datos nunca los ve — más lógica en el cliente, pero es lógica que
le corresponde a él, no a la base de datos.

## D010 — Patrón de diseño aplicado y por qué

**Decision:** dos patrones, cada uno resolviendo un problema concreto ya presente en el
código, no anticipado:

**1. Strategy** — `backend/domain/ports.py` define `PasswordHasher`, `TokenService`,
`EmbeddingProvider`, `LLMProvider` como interfaces (`ABC`); `backend/infrastructure/`
contiene exactamente una implementación concreta de cada una (`BcryptPasswordHasher`,
`JwtTokenService`, `LocalHashEmbeddingProvider` — reemplazada por el proveedor real en la
Fase 18 —). Los casos de uso (`LoginUseCase`, etc.) dependen de la interfaz, nunca de la
implementación concreta.

**Why:** el plan exige explícitamente que LLM/embeddings sean intercambiables ("interfaz
pequeña, un solo proveedor real detrás") — Strategy es el patrón que resuelve exactamente
eso: cambiar de proveedor es escribir una clase nueva que implemente el puerto, sin tocar
`application/` ni `presentation/`. `tests/test_fase13_clean_architecture.py` lo verifica de
forma automática (ningún import de SDK externo en `domain/`), no solo de palabra.

**2. Repository** — `UserRepository`/`MessageRepository` (interfaces en `domain/ports.py`) +
`PsycopgUserRepository`/`PsycopgMessageRepository` (implementación en `infrastructure/`).

**Why:** los casos de uso necesitan persistencia sin saber que es PostgreSQL/psycopg — eso es
justo lo que exige la Clean Architecture del plan (R16: dominio sin el driver de Postgres).
Además, cada método del repositorio es deliberadamente una operación de negocio completa
(`create`, `edit`, `soft_delete`, `list_by_channel`, `search`) y no un CRUD genérico — el
repositorio nunca decide autorización por su cuenta, delega esa decisión a RLS (principio
central del proyecto), evitando el antipatrón de "Repository que reimplementa permisos en
Python".

**Alternatives:** Factory para instanciar proveedores según config (descartado — con un solo
proveedor real detrás no hay nada que fabricar condicionalmente todavía; se puede introducir
si algún día hay más de uno, no antes — YAGNI); Active Record en vez de Repository (mezclaría
persistencia con entidades de dominio, y `domain/entities.py` dejaría de ser Python puro).

**Trade-off:** una capa de indirección (la interfaz) para algo que hoy solo tiene una
implementación real — el costo es aceptado porque el requisito de intercambiabilidad ya está
explícitamente en el enunciado del plan, no es especulación.

## D011 — Scope cuts

**Cut #1 — Sin endpoints de gestión de canales (crear canal, agregar/quitar miembros).**
**Context:** Fase 5 (ACL de canales) tentaba a construir casos de uso completos de
administración de canal ("owner administra canal y miembros").
**Why:** la lista de endpoints de la Fase 16 (`POST /auth/login`, `GET /channels`,
`GET/POST /channels/{id}/messages`, `PATCH/DELETE /messages/{id}`, `GET /messages/search`,
`POST/GET /copilot/*`) no incluye ningún `POST/PATCH /channels` ni gestión de miembros — el
escenario de demo se resuelve completo con el seed (Fase 3). Construir esos endpoints sería
una abstracción sin caso de uso real que la consuma (regla dura del proyecto).
**Alternatives:** implementarlos "por si acaso" para verse más completo — descartado, va en
contra del STOP RULE ("no introducir abstracciones sin necesidad concreta ya presente").
**Trade-off:** `rw_channel_members` no tiene policies de INSERT/UPDATE/DELETE (Fase 5); si en
algún momento se agrega un endpoint real de gestión de canal, esa policy se escribe entonces,
respaldada por el caso de uso que la necesite.

**Cut #2 — Función `rw_is_channel_member()` con `SECURITY DEFINER` (justificación, R17).**
**Context:** una policy de `rw_channel_members` que hace `SELECT` sobre la propia
`rw_channel_members` dispara "infinite recursion detected in policy" en PostgreSQL — la
subconsulta reevalúa la misma policy que la está evaluando a ella.
**Why:** `SECURITY DEFINER` hace que la función corra con los privilegios de quien la creó
(el rol admin), evitando que su `SELECT` interno vuelva a pasar por RLS — rompe la recursión.
No elude ninguna policy de negocio: solo expone un booleano (`¿user_id es miembro de
channel_id?`), nunca filas, y su `EXECUTE` está revocado de `PUBLIC` y otorgado solo a
`rw_app` (`database/functions/0001_is_channel_member.sql`).
**Alternatives:** duplicar la condición de membresía como una vista materializada o
desnormalizar el flag en cada fila (más complejidad y una fuente de verdad adicional que
mantener sincronizada, sin necesidad real).
**Trade-off:** cualquier cambio a "qué significa ser miembro de un canal" ahora vive en un
solo lugar (la función) en vez de estar duplicado en 3 policies — ventaja, no solo costo.

**Cut #3 — Frontend: tokens en `localStorage`, sin router, sin librería de i18n.**
**Context:** Fase 17 (frontend) podía tirar hacia `react-router` (no hay más de una "página"
real — login vs. app autenticada, resuelto con un `if` sobre el estado de auth), una librería
de i18n como `i18next` (con 2 idiomas y ~25 strings, un `Record` + `Context` propio alcanza),
o guardar los tokens en cookies `httpOnly` (requiere que el backend las emita, CSRF, y no es
lo que expone la API que ya se construyó — Bearer token en `Authorization`).
**Why:** cada una de esas herramientas resuelve un problema que este alcance no tiene todavía
— agregarlas ahora sería la abstracción sin necesidad concreta que el STOP RULE prohíbe.
**Trade-off aceptado conscientemente:** `localStorage` es legible por cualquier script que
logre inyectarse en la página (XSS) — el mismo trade-off que casi cualquier SPA con Bearer
tokens acepta sin backend con sesiones de cookie. Mitigado en parte por: el `SearchHighlight`
nunca usa `dangerouslySetInnerHTML` sobre contenido de mensajes (dato no confiable, R10), y
los access tokens viven poco (`JWT_ACCESS_TOKEN_EXPIRES_MINUTES=15`).

## D012 — Origen de nombre/cargo del usuario en el copiloto (JWT claims vs lookup server-side)

**Decision: Opción B, lookup server-side.** `AskCopilotUseCase` recibe el `user_id` (del JWT
verificado, como siempre) y hace `UserRepository.find_by_id(user_id)` para obtener
`full_name`/`role_title` frescos de `rw_users` en cada pregunta — nunca los toma de claims
del JWT.

**Context:** el JWT de este proyecto (Fase 4) se diseñó deliberadamente mínimo (`sub` + claims
estándar) para no adelantar esta decisión antes de tiempo. Con el copiloto ya en construcción,
tocaba elegir.

**Why:** `GetCurrentUserUseCase`/`PsycopgUserRepository.find_by_id()` ya existían (Fase 14,
para `GET /users/me`) — reusarlos para el copiloto es cero código nuevo de infraestructura.
Además, evita el problema real de la Opción A: si el cargo de alguien cambia, un JWT de
Opción A quedaría desactualizado hasta el próximo login/refresh (hasta
`JWT_ACCESS_TOKEN_EXPIRES_MINUTES=15`), mientras que el lookup server-side siempre refleja
`rw_users` tal como está en ese instante.

**Alternatives:** Opción A (claims en el JWT) — evita una query por pregunta, pero introduce
staleness y hubiera obligado a rediseñar el JWT ya construido en la Fase 4.

**Trade-off:** una query adicional a `rw_users` por cada pregunta al copiloto — no es RLS (esa
tabla no la tiene, Fase 4/5), así que es una consulta barata por PK; irrelevante frente al
costo de la llamada al LLM que de todos modos ocurre en la misma request.

---

## D013 — Reuse detection: revocar toda la cadena, no solo el token reutilizado

**Decision:** cuando `RefreshTokenUseCase` detecta que un token ya revocado se presenta de
nuevo, revoca **todos** los refresh tokens activos de ese usuario (`revoke_all_active_for_user`),
no solo el token reutilizado.

**Context:** Fase 15 exige "reuse detection: token revocado reutilizado → DENY" — el plan no
especifica el alcance de la respuesta, solo que debe denegarse.

**Why:** la reutilización de un token ya rotado tiene una sola explicación razonable: alguien
más (un atacante) tiene una copia del token A y lo usó, o la víctima lo está usando después
de que un atacante ya rotó A→B primero. En cualquiera de los dos casos, no hay forma de saber
—solo con esta señal— cuál de las dos cadenas (la del atacante o la de la víctima) sigue
siendo legítima. La respuesta segura es asumir que **toda** la sesión está comprometida y
forzar un login nuevo, no intentar adivinar cuál mitad de la cadena "salvar".

**Alternatives:** revocar solo el token reutilizado (A) y dejar viva su cadena descendiente
(B) — más conveniente para el usuario legítimo, pero si el atacante fue quien generó B
(robó A y rotó primero), esto le dejaría una sesión válida activa; deshabilitar la cuenta
completa hasta intervención manual (demasiado disruptivo para el alcance de esta prueba, sin
flujo de soporte que lo justifique).

**Trade-off:** un usuario legítimo cuyo token viejo se reutilizó por error (ej. un cliente con
un bug que reintenta la request de refresh) pierde **todas** sus sesiones activas, no solo
una — se acepta porque el costo de un falso positivo (volver a loguearse) es mucho menor que
el costo de un falso negativo (sesión de atacante viva).

## D014 — Mensajes directos: reutilizar rw_channels/rw_channel_members, no una entidad nueva

**Decision:** un DM es una fila más de `rw_channels` con `is_direct = true`, `name = NULL` y
exactamente 2 filas en `rw_channel_members`. `rw_get_or_create_dm_channel()` (SECURITY
DEFINER) es la única vía para crearlo.

**Context:** ampliación post-alcance-original pedida explícitamente por el usuario (feature
de UI, no parte de las 24 fases originales) — mostrar mensajes directos junto a los canales.

**Why:** toda la RLS de `rw_channels`/`rw_messages` (Fase 4/6) ya es genérica por membresía —
un DM funciona con las policies de SELECT/INSERT/UPDATE existentes sin tocar una sola línea,
y `send_message`/`get_channel_messages`/`search_messages` funcionan igual para un DM que para
un canal. Un modelo paralelo (tabla `rw_direct_messages` separada) hubiera duplicado toda esa
lógica de autorización sin necesidad real.

**Alternatives:** entidad `rw_direct_conversations` independiente con sus propias policies
(más "correcto" en un dominio más grande, pero D011 ya establece "no crear abstracciones sin
necesidad concreta" — aquí el canal existente cubre el caso sin fricción).

**Trade-off:** `rw_channels.name` pasó de `NOT NULL` a nullable, y ganó un segundo CHECK
(`NOT is_direct OR name IS NULL`) — cualquier código futuro que asuma `channel_name` siempre
presente debe filtrar por `is_direct` primero. `rw_channel_members` sigue sin policy de
INSERT/UPDATE/DELETE (D011): crear membresías solo es posible a través de la función
SECURITY DEFINER, nunca por INSERT directo de `rw_app`.

## D015 — Presencia: tracker en memoria de un solo proceso + receiver dedicado para detectar cierre

**Decision:** `PresenceTracker` (mismo criterio single-process que `ChannelBroadcaster`, D008)
cuenta conexiones activas por usuario. El endpoint `/ws/presence` corre dos tareas
concurrentes por conexión: un `sender` (reenvía eventos de la cola) y un `receiver` que solo
hace `await websocket.receive()` en loop, sin usar lo que llega.

**Context:** ampliación post-alcance pedida por el usuario (punto verde online/offline).

**Why:** un socket que solo envía (como ya hacía `channel_websocket`, Fase 7) nunca detecta
que el cliente cerró la pestaña hasta el próximo intento de `send()` — y si nadie más se
conecta/desconecta después, ese intento nunca llega, dejando al usuario "online" para
siempre. Verificado en vivo: sin el `receiver`, cerrar la pestaña de un usuario no bajaba su
estado ni después de varios segundos; con el `receiver` corriendo en paralelo (que sí dispara
`WebSocketDisconnect` al primer frame de cierre real del socket), el cambio a offline es
inmediato. `channel_websocket` tiene la misma limitación de fondo pero ahí es inofensiva (una
suscripción inerte en un dict en memoria, sin efecto visible) — se documenta aquí, no se
corrigió ahí, por estar fuera del pedido concreto de esta ronda.

**Alternatives:** heartbeat/ping periódico desde el cliente (más código en el frontend, mismo
resultado); asumir online mientras el proceso del backend no reinicie (inaceptable, el punto
verde mentiría indefinidamente).

**Trade-off:** cada conexión de presencia mantiene 2 tareas asyncio en vez de 1 — costo
trivial para el volumen de esta prueba, pero no escala igual que un enfoque basado en
heartbeats si el número de conexiones concurrentes creciera mucho.

## D016 — Contador de no leídos: tabla de "última lectura", no un flag por mensaje

**Decision:** `rw_channel_reads (channel_id, user_id, last_read_at)` — un `unread_count` se
calcula contando mensajes de otros posteriores a `last_read_at`, no marcando cada mensaje
individual como leído/no leído por usuario.

**Context:** ampliación post-alcance pedida por el usuario (badge de no leídos por canal).

**Why:** una fila por (canal, usuario) escala igual sin importar cuántos mensajes tenga el
canal — marcar como leído es un solo UPSERT, no un UPDATE masivo sobre N mensajes. Es el mismo
patrón que usan Slack/Discord internamente.

**Alternatives:** columna `read_by uuid[]` en `rw_messages` (crece sin límite, requiere
reescribir la fila del mensaje por cada usuario que lo lee); tabla `rw_message_reads
(message_id, user_id)` de grano fino (permite saber "quién leyó qué mensaje exacto", dato que
ningún requisito pide y que multiplicaría filas por mensaje × miembro).

**Trade-off:** no hay recibo de lectura por mensaje individual (no se puede responder "¿Alice
ya vio ESTE mensaje en particular?"), solo "hasta qué instante leyó el canal" — suficiente
para el badge, no para un check de "visto" estilo WhatsApp.
