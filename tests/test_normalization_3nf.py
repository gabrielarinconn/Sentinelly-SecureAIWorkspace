"""R01 — normalización 3FN. Cierra el gap documentado en docs/TRACEABILITY.md: el modelo
estaba normalizado hasta 3FN (docs/erd/normalization.md) desde la Fase 3, pero sin evidencia
automatizada (marcado 🟡 desde la Fase 20).

Corre contra el catálogo real de PostgreSQL (information_schema/pg_constraint) y contra datos
reales del seed — no contra una copia hardcodeada del esquema — así que si una migración
futura reintroduce una columna denormalizada, este test la detecta.
"""

from backend.application.login import LoginUseCase
from backend.infrastructure.db import authorized_transaction, get_app_connection
from backend.infrastructure.jwt_service import JwtTokenService
from backend.infrastructure.password_hasher import BcryptPasswordHasher
from backend.infrastructure.user_repository import PsycopgUserRepository

RW_TABLES = [
    "rw_users",
    "rw_channels",
    "rw_channel_members",
    "rw_channel_reads",
    "rw_messages",
    "rw_message_history",
    "rw_message_embeddings",
    "rw_refresh_tokens",
    "rw_copilot_usage",
]

# Atributos que dependen únicamente de la PK de su propia tabla ("dueños"). 3FN exige que
# ninguna OTRA tabla los almacene directamente — deben obtenerse siempre vía JOIN por FK, nunca
# por una copia local que dependería transitivamente (ej. sender_id -> rw_users.full_name).
OWNED_ATTRIBUTES = {
    "rw_users": {"email", "password_hash", "full_name", "role_title", "is_active"},
    "rw_channels": {"name", "is_private", "is_direct", "created_by"},
}


def _columns_by_table(cur) -> dict[str, set[str]]:
    cur.execute(
        "SELECT table_name, column_name FROM information_schema.columns "
        "WHERE table_schema = 'public' AND table_name = ANY(%s)",
        (RW_TABLES,),
    )
    result: dict[str, set[str]] = {}
    for table_name, column_name in cur.fetchall():
        result.setdefault(table_name, set()).add(column_name)
    return result


def test_every_rw_table_has_an_explicit_primary_key():
    """1FN/2FN: sin una PK real no hay forma de hablar de dependencia funcional sobre 'la clave
    completa' — condición previa a cualquier razonamiento de normalización."""
    conn = get_app_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT table_name FROM information_schema.table_constraints "
                "WHERE constraint_type = 'PRIMARY KEY' AND table_schema = 'public' AND table_name = ANY(%s)",
                (RW_TABLES,),
            )
            tables_with_pk = {row[0] for row in cur.fetchall()}
    finally:
        conn.close()
    missing = set(RW_TABLES) - tables_with_pk
    assert not missing, f"Tablas sin PK explícita (rompe 1FN/2FN): {missing}"


def test_no_table_stores_a_denormalized_copy_of_another_entitys_attributes():
    """3FN: un atributo transitivamente dependiente (ej. rw_messages.sender_name, que
    dependería de sender_id -> rw_users.full_name, no directamente de rw_messages.id) es la
    violación clásica de 3FN. Ninguna tabla salvo la dueña debe tener esas columnas — todo
    acceso a nombre/cargo/email de usuario o nombre/privacidad de canal pasa por un JOIN sobre
    la FK, nunca por una copia local."""
    conn = get_app_connection()
    try:
        with conn.cursor() as cur:
            columns = _columns_by_table(cur)
    finally:
        conn.close()

    violations = []
    for owner_table, attrs in OWNED_ATTRIBUTES.items():
        for table_name, table_columns in columns.items():
            if table_name == owner_table:
                continue
            leaked = attrs & table_columns
            if leaked:
                violations.append(f"{table_name} almacena {leaked}, que pertenece a {owner_table}")

    assert not violations, "\n".join(violations)


def test_messages_reference_sender_and_channel_only_by_foreign_key():
    """Caso concreto del test anterior, nombrado explícitamente porque es el ejemplo de libro
    de texto de 3FN: rw_messages solo tiene sender_id/channel_id (FK), nunca un
    sender_name/channel_name copiado."""
    conn = get_app_connection()
    try:
        with conn.cursor() as cur:
            columns = _columns_by_table(cur)["rw_messages"]
    finally:
        conn.close()
    assert {"sender_id", "channel_id"} <= columns
    assert not {"sender_name", "sender_email", "sender_role_title", "channel_name"} & columns


def test_composite_key_tables_have_no_partial_key_dependency():
    """2FN: en una tabla con PK compuesta, un atributo no-clave no puede depender de solo una
    parte de la clave. Se demuestra con datos reales, no solo inspeccionando el esquema: si
    'role' (rw_channel_members) dependiera solo de user_id, un mismo usuario tendría el mismo
    rol en todos sus canales. El seed prueba que no es así (Bob es 'member' en #general y
    'owner' en #leadership-private) — confirma que role depende del PAR completo
    (channel_id, user_id), no de una mitad.

    Se consulta como Bob (RLS real, no una conexión admin que bypasea permisos) — Bob es
    miembro de ambos canales, así que la policy de SELECT de rw_channel_members
    (rw_is_channel_member) le deja ver todas las filas de ambos, incluidas las suyas con
    roles distintos."""
    conn = get_app_connection()
    try:
        login = LoginUseCase(
            user_repository=PsycopgUserRepository(conn),
            password_hasher=BcryptPasswordHasher(),
            token_service=JwtTokenService(),
        )
        bob_id = JwtTokenService().decode_access_token(login.execute("bob@sentinel.dev", "DemoPass123!").access_token)
        with authorized_transaction(conn, bob_id):
            with conn.cursor() as cur:
                cur.execute("SELECT channel_id, user_id, role FROM rw_channel_members;")
                rows = cur.fetchall()
    finally:
        conn.close()

    roles_by_user: dict[str, set[str]] = {}
    for _channel_id, user_id, role in rows:
        roles_by_user.setdefault(str(user_id), set()).add(role)

    varying = {u: r for u, r in roles_by_user.items() if len(r) > 1}
    assert varying, (
        "El seed no tiene un usuario con roles distintos en canales distintos — no se puede "
        "demostrar empíricamente que 'role' depende del PAR (channel_id, user_id) y no de "
        "user_id solo (2FN)."
    )
