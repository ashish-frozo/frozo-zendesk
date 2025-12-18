web: uvicorn api.main:app --host 0.0.0.0 --port $PORT --workers 2
worker: celery -A worker.celery_app worker --loglevel=info --concurrency=2
