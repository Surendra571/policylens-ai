#!/bin/sh
set -e

echo "[PolicyLens Entrypoint] Initializing container runtime..."

# Wait for PostgreSQL
if [ -n "$POSTGRES_HOST" ]; then
    echo "[PolicyLens Entrypoint] Waiting for PostgreSQL at $POSTGRES_HOST:${POSTGRES_PORT:-5432}..."
    while ! python -c "
import socket
import os
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.settimeout(2)
try:
    s.connect(('$POSTGRES_HOST', int(os.environ.get('POSTGRES_PORT', 5432))))
    s.close()
    exit(0)
except Exception:
    exit(1)
" > /dev/null 2>&1; do
        echo "[PolicyLens Entrypoint] PostgreSQL is unavailable - sleeping 1s"
        sleep 1
    done
    echo "[PolicyLens Entrypoint] PostgreSQL is ready and accepting connections."
fi

# Apply migrations and collect static files for web servers
if [ "$1" = "gunicorn" ] || [ "$1" = "python" ]; then
    echo "[PolicyLens Entrypoint] Applying database migrations..."
    python manage.py migrate --noinput

    if [ "$COLLECT_STATIC" = "1" ] || [ "$COLLECT_STATIC" = "true" ]; then
        echo "[PolicyLens Entrypoint] Collecting static assets..."
        python manage.py collectstatic --noinput --clear || true
    fi
fi

echo "[PolicyLens Entrypoint] Executing command: $@"
exec "$@"

