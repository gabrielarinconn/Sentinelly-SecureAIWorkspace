# Documentación de API

`openapi.json` es la especificación OpenAPI 3.1 exportada en frío desde el backend en
ejecución (`GET /openapi.json`, autogenerado por FastAPI a partir de los modelos Pydantic y
las rutas reales — nunca se escribe a mano, así que nunca queda desincronizado del código).

Cómo regenerarlo tras un cambio de API (con el backend corriendo, `docker compose up` o
`uvicorn` local):

```bash
curl -s http://localhost:8000/openapi.json | python -m json.tool > docs/api/openapi.json
```

## Cómo verlo

- **Swagger UI en vivo** (interactivo, "Try it out"): con el backend corriendo, abrir
  `http://localhost:8000/docs`.
- **Sin correr nada**: importar `openapi.json` en
  [Swagger Editor](https://editor.swagger.io/) (File → Import file) o en Postman
  (Import → File) para navegar la spec o generar una colección ejecutable.

## Endpoints REST (13 rutas, 15 operaciones — ver `openapi.json`)

Auth, canales/mensajes, búsqueda, mensajes directos, copiloto — todos documentados con sus
modelos de request/response, en `openapi.json`.

## Endpoints WebSocket (no cubiertos por OpenAPI — el estándar no soporta WS)

| Ruta | Auth | Uso |
|---|---|---|
| `GET /ws/channels/{channel_id}?token=<jwt>` | JWT en query param (el navegador no permite header `Authorization` en el handshake de WS) | Suscribe al cliente a los eventos `message_created`/`message_edited`/`message_deleted` de ese canal. Rechaza (código 4403) si el actor no es miembro del canal; rechaza (4401) si el token es inválido. |
| `GET /ws/presence?token=<jwt>` | Igual, JWT en query param | Socket único por sesión (no por canal): al conectar recibe un `presence_snapshot` con los `user_ids` actualmente en línea, y después eventos `presence_changed` en tiempo real conforme otros usuarios se conectan/desconectan. |

Ambos verificados en `backend/presentation/api.py` (`channel_websocket`, `presence_websocket`)
y con tests en `tests/test_fase7_realtime.py`.
