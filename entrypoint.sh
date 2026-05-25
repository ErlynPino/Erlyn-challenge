#!/bin/sh
alembic upgrade head || echo "[entrypoint] WARNING: migration failed, proceeding"
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8080}"
