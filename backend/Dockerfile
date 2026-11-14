FROM python:3.12-slim-bookworm
COPY --from=ghcr.io/astral-sh/uv:0.5.11 /uv /usr/local/bin/uv
WORKDIR /srv
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY . .
# The app only reads its files; run it unprivileged.
RUN useradd --system --uid 10001 --no-create-home --shell /usr/sbin/nologin app
USER app
ENV PATH="/srv/.venv/bin:$PATH" PYTHONDONTWRITEBYTECODE=1
EXPOSE 8000
# One worker: the rate limiters are in-memory. No uvicorn access log: app.request is the access
# log (it redacts card ids and never logs query strings).
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:create_app --factory --host 0.0.0.0 --port 8000 --workers 1 --no-access-log"]
