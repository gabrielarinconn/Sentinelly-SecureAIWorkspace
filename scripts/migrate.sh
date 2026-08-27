#!/usr/bin/env bash
# Aplica database/{migrations,policies,triggers,functions,views}/*.sql en ese orden contra el
# contenedor de PostgreSQL de docker-compose. Idempotente: registra cada archivo aplicado
# (con su carpeta) en schema_migrations.
set -euo pipefail
cd "$(dirname "$0")/.."

SERVICE="postgres"
DB_USER="${POSTGRES_USER:-sentinel_app}"
DB_NAME="${POSTGRES_DB:-bd_gabriela_rincon_nakamoto}"

psql_exec() {
    docker compose exec -T "$SERVICE" psql -v ON_ERROR_STOP=1 -U "$DB_USER" -d "$DB_NAME" \
        -v db_name="$DB_NAME" \
        -v rw_app_password="${RW_APP_PASSWORD:-}" \
        "$@"
}

psql_exec -c "CREATE TABLE IF NOT EXISTS schema_migrations (id text PRIMARY KEY, applied_at timestamptz NOT NULL DEFAULT now());"

for dir in database/migrations database/functions database/procedures database/policies database/triggers database/views; do
    [ -d "$dir" ] || continue
    shopt -s nullglob
    files=("$dir"/*.sql)
    shopt -u nullglob
    for file in $(printf '%s\n' "${files[@]}" | sort); do
        id="${dir#database/}/$(basename "$file")"
        applied="$(psql_exec -tAc "SELECT 1 FROM schema_migrations WHERE id = '$id';")"
        if [ "$applied" = "1" ]; then
            echo "skip   $id (already applied)"
            continue
        fi
        echo "apply  $id"
        psql_exec -f - < "$file"
        psql_exec -c "INSERT INTO schema_migrations (id) VALUES ('$id');"
    done
done

echo "Migrations up to date."
