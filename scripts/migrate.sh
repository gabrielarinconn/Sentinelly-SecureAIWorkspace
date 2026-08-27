#!/usr/bin/env bash
# Aplica database/migrations/*.sql en orden contra el contenedor de PostgreSQL de
# docker-compose. Idempotente: registra cada migración aplicada en schema_migrations.
set -euo pipefail
cd "$(dirname "$0")/.."

SERVICE="postgres"
DB_USER="${POSTGRES_USER:-sentinel_app}"
DB_NAME="${POSTGRES_DB:-bd_gabriela_rincon_nakamoto}"
MIGRATIONS_DIR="database/migrations"

psql_exec() {
    docker compose exec -T "$SERVICE" psql -v ON_ERROR_STOP=1 -U "$DB_USER" -d "$DB_NAME" "$@"
}

psql_exec -c "CREATE TABLE IF NOT EXISTS schema_migrations (id text PRIMARY KEY, applied_at timestamptz NOT NULL DEFAULT now());"

for file in $(ls "$MIGRATIONS_DIR"/*.sql | sort); do
    name="$(basename "$file")"
    applied="$(psql_exec -tAc "SELECT 1 FROM schema_migrations WHERE id = '$name';")"
    if [ "$applied" = "1" ]; then
        echo "skip   $name (already applied)"
        continue
    fi
    echo "apply  $name"
    psql_exec -f - < "$file"
    psql_exec -c "INSERT INTO schema_migrations (id) VALUES ('$name');"
done

echo "Migrations up to date."
