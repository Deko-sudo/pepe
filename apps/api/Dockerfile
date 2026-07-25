FROM python:3.12-slim

WORKDIR /workspace

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY packages/quote-core /workspace/packages/quote-core
COPY apps/api /workspace/apps/api
WORKDIR /workspace/apps/api
RUN pip install --no-cache-dir /workspace/packages/quote-core \
    && pip install --no-cache-dir ".[dev]"

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
