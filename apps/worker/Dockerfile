FROM python:3.12-slim

WORKDIR /workspace

COPY packages/quote-core /workspace/packages/quote-core
COPY apps/worker /workspace/apps/worker
WORKDIR /workspace/apps/worker
RUN pip install --no-cache-dir /workspace/packages/quote-core \
    && pip install --no-cache-dir ".[dev]"

# Consume the explicitly routed quote and candle queues in addition to Celery's default queue.
# Expand queue settings at runtime so Compose environment overrides stay effective.
CMD ["sh", "-c", "exec celery -A app.celery_app worker --loglevel=info --concurrency=2 --queues=celery,${QUOTE_QUEUE_NAME:-quotes},${CANDLE_QUEUE_NAME:-candles}"]
