#!/bin/sh
# If DATABASE_URL is set (e.g. Railway's Postgres service), parse it, wait
# for the database to become reachable, then run alembic migrations before
# starting the app. If DATABASE_URL is not set, skip alembic entirely and
# start the app immediately (dev/SQLite mode).

DB_HOST=""
DB_PORT=""

if [ -n "$DATABASE_URL" ]; then
  DB_INFO=$(python -c "
import sys
from urllib.parse import urlparse

url = '''$DATABASE_URL'''.strip()
try:
    parsed = urlparse(url)
    host = parsed.hostname
    port = parsed.port or 5432
    if not host:
        sys.exit(1)
    print(f'{host} {port}')
except Exception:
    sys.exit(1)
" 2>/dev/null)

  if [ $? -eq 0 ] && [ -n "$DB_INFO" ]; then
    DB_HOST=$(echo "$DB_INFO" | awk '{print $1}')
    DB_PORT=$(echo "$DB_INFO" | awk '{print $2}')
  fi
fi

if [ -n "$DB_HOST" ]; then
  echo "DATABASE_URL is set, waiting for database at $DB_HOST:$DB_PORT..."
  for i in $(seq 1 60); do
    if python -c "import socket,sys; s=socket.create_connection(('$DB_HOST',$DB_PORT),2); s.close()" 2>/dev/null; then
      echo "db ready after $i tries"
      break
    fi
    echo "try $i: db not ready, sleep 2s"
    sleep 2
  done

  echo "running alembic upgrade head..."
  alembic upgrade head
  rc=$?
  if [ $rc -ne 0 ]; then
    echo "alembic failed rc=$rc"
    exit $rc
  fi
else
  echo "DATABASE_URL not set or invalid, skipping alembic (dev/SQLite mode)"
fi

echo "starting uvicorn..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
