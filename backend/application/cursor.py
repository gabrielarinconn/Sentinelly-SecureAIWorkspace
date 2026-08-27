import base64
import json
from datetime import datetime
from typing import Optional


def encode_cursor(created_at: datetime, id_: str) -> str:
    payload = json.dumps([created_at.isoformat(), id_])
    return base64.urlsafe_b64encode(payload.encode("utf-8")).decode("ascii")


def decode_cursor(cursor: Optional[str]) -> tuple[Optional[datetime], Optional[str]]:
    """Cursor opaco (D005) — el cliente nunca construye ni interpreta su contenido, solo lo
    devuelve tal cual lo recibió en la página anterior."""
    if not cursor:
        return None, None
    payload = base64.urlsafe_b64decode(cursor.encode("ascii")).decode("utf-8")
    created_at_iso, id_ = json.loads(payload)
    return datetime.fromisoformat(created_at_iso), id_
