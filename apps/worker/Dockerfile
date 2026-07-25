FROM python:3.12-slim

WORKDIR /workspace

COPY packages/quote-core /workspace/packages/quote-core
COPY apps/worker /workspace/apps/worker
WORKDIR /workspace/apps/worker
RUN pip install --no-cache-dir /workspace/packages/quote-core \
    && pip install --no-cache-dir ".[dev]"

CMD ["python", "-m", "app.main"]
