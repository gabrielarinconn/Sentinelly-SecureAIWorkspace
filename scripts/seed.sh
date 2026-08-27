#!/usr/bin/env bash
# Carga database/seeds/*.sql en orden. No es idempotente a propósito: reinstalar el seed
# sobre datos existentes debe fallar visiblemente (PK/UNIQUE), no duplicar silenciosamente.
set -euo pipefail
cd "$(dirname "$0")/.."

SERVICE="postgres"
DB_USER="${POSTGRES_USER:-sentinel_app}"
DB_NAME="${POSTGRES_DB:-bd_gabriela_rincon_nakamoto}"
SEEDS_DIR="database/seeds"

for file in $(ls "$SEEDS_DIR"/*.sql | sort); do
    echo "seed   $(basename "$file")"
    docker compose exec -T "$SERVICE" psql -v ON_ERROR_STOP=1 -U "$DB_USER" -d "$DB_NAME" -f - < "$file"
done

echo "Seed loaded."
