# Build stage
FROM python:3.11-slim AS build
WORKDIR /app
COPY requirements.txt requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r requirements-dev.txt
COPY . .
ENV PYTHONPATH=/app
CMD ["pytest", "-q"]

# Runtime stage
FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*
RUN useradd -m appuser
COPY --from=build /usr/local/lib/python3.11 /usr/local/lib/python3.11
COPY --from=build /usr/local/bin /usr/local/bin
COPY . .
COPY wait-for-vault.sh /usr/local/bin/wait-for-vault.sh
RUN chmod +x /usr/local/bin/wait-for-vault.sh
EXPOSE 8000
HEALTHCHECK CMD curl -f http://localhost:8000/health || exit 1
USER appuser
ENV PYTHONUNBUFFERED=1
CMD ["sh", "-c", "wait-for-vault.sh uvicorn app.main:app --host 0.0.0.0 --port 8000"]
