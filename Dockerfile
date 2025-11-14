# Build stage
FROM python:3.12-slim@sha256:d86b4c74b936c438cd4cc3a9f7256b9a7c27ad68c7caf8c205e18d9845af0164 AS build
WORKDIR /app
COPY pyproject.toml poetry.lock ./
RUN pip install --no-cache-dir "poetry==1.8.4" && \
    poetry config virtualenvs.create false && \
    poetry install --only main --no-interaction --no-ansi --no-root && \
    pip uninstall -y poetry
COPY . .

# Test stage
FROM python:3.12-slim@sha256:d86b4c74b936c438cd4cc3a9f7256b9a7c27ad68c7caf8c205e18d9845af0164 AS test
WORKDIR /app
RUN pip install --no-cache-dir "poetry==1.8.4"
COPY --from=build /usr/local /usr/local
COPY --from=build /app /app
RUN poetry config virtualenvs.create false && \
    poetry install --with dev --no-interaction --no-ansi --no-root && \
    pip uninstall -y poetry
CMD ["pytest", "-q"]

# Runtime stage
FROM python:3.12-slim@sha256:d86b4c74b936c438cd4cc3a9f7256b9a7c27ad68c7caf8c205e18d9845af0164 AS runtime
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app
RUN groupadd -r app && useradd -r -m -g app app
# hadolint ignore=DL3008
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*
COPY --from=build /usr/local /usr/local
COPY --from=build --chown=app:app /app /app
USER app
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:8080/ || exit 1
EXPOSE 8080
CMD ["python","-m","http.server","8080","--bind","0.0.0.0"]
