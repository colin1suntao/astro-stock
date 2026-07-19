#!/bin/sh
# Wait for db ready, run alembic migration, then start uvicorn
echo "waiting for db..."
for i in $(seq 1 60); do
  if python -c "import socket,sys; s=socket.create_connection(('db',5432),2); s.close()" 2>/dev/null; then
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

echo "starting uvicorn..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
