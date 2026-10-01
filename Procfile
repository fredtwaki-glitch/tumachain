web: cd backend && (alembic upgrade head || echo "alembic upgrade skipped; relying on self-healing schema bootstrap") && uvicorn app.main:app --host 0.0.0.0 --port $PORT
