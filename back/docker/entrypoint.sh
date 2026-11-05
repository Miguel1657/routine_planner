#!/bin/sh
set -e

# Import the exercises dataset on first start (or if the DB was wiped).
# The data volume keeps it across redeploys. Set FORCE_DATASET_IMPORT=1 to re-import.
DB_FILE="/app/${DATABASE_PATH:-data/app.db}"
if [ ! -s "$DB_FILE" ] || [ "${FORCE_DATASET_IMPORT:-0}" = "1" ]; then
    echo "[entrypoint] Importing exercises dataset into $DB_FILE ..."
    python -m src.dataset_loader
fi

exec "$@"
