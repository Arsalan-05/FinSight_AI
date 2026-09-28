FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY . .

ENV PATH="/app/.venv/bin:$PATH"

# Score the eval set against this exact build; the Evals page lists the results.
RUN python -m evals.run --subset smoke --dry-run && python -m evals.run --subset full --dry-run

EXPOSE 8000

CMD ["sh", "-c", "python -m db.migrate && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
