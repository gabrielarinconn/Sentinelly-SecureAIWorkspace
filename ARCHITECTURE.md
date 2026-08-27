# Architecture

## Principio central

> The LLM never decides what the user is allowed to see. PostgreSQL decides what context can
> be retrieved; the LLM only reasons over authorized context. Authorization happens before
> generation.

## Capas

```text
Frontend → Backend → PostgreSQL → RLS
```

El frontend no es frontera de seguridad. El backend tampoco es la única. PostgreSQL es la
última barrera.

_El resto de este documento (diagramas, flujo de retrieval, Clean Architecture del backend,
justificación de patrones) se completa a medida que avanzan las fases del proyecto._
