#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

if [ -f ".env" ]; then
  set -a
  # shellcheck disable=SC1091
  source ".env"
  set +a
fi

POSTGRES_USER="${POSTGRES_USER:-porfacan}"
POSTGRES_DB="${POSTGRES_DB:-porfacan}"
POSTGRES_TEST_DB="${POSTGRES_TEST_DB:-porfacan_test}"
RABBITMQ_USER="${RABBITMQ_USER:-porfacan}"
RABBITMQ_PASSWORD="${RABBITMQ_PASSWORD:-porfacan}"
RABBITMQ_VHOST="${RABBITMQ_VHOST:-porfacan}"

echo "[bootstrap] Starting postgres, redis, rabbitmq"
docker compose -f docker-compose.dev.yml up -d db redis rabbitmq

echo "[bootstrap] Waiting for postgres to become ready"
until docker compose -f docker-compose.dev.yml exec -T db pg_isready -U "$POSTGRES_USER" >/dev/null 2>&1; do
  sleep 1
done

echo "[bootstrap] Ensuring databases exist"
APP_DB_EXISTS="$(docker compose -f docker-compose.dev.yml exec -T db psql -U "$POSTGRES_USER" -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='${POSTGRES_DB}'")"
if [ "$APP_DB_EXISTS" != "1" ]; then
  docker compose -f docker-compose.dev.yml exec -T db psql -U "$POSTGRES_USER" -d postgres -c "CREATE DATABASE \"${POSTGRES_DB}\" OWNER \"${POSTGRES_USER}\";"
fi

TEST_DB_EXISTS="$(docker compose -f docker-compose.dev.yml exec -T db psql -U "$POSTGRES_USER" -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='${POSTGRES_TEST_DB}'")"
if [ "$TEST_DB_EXISTS" != "1" ]; then
  docker compose -f docker-compose.dev.yml exec -T db psql -U "$POSTGRES_USER" -d postgres -c "CREATE DATABASE \"${POSTGRES_TEST_DB}\" OWNER \"${POSTGRES_USER}\";"
fi

echo "[bootstrap] Waiting for rabbitmq to become ready"
until docker compose -f docker-compose.dev.yml exec -T rabbitmq rabbitmq-diagnostics -q ping >/dev/null 2>&1; do
  sleep 1
done

echo "[bootstrap] Ensuring rabbitmq vhost/user exist"
docker compose -f docker-compose.dev.yml exec -T rabbitmq rabbitmqctl add_vhost "$RABBITMQ_VHOST" >/dev/null 2>&1 || true
docker compose -f docker-compose.dev.yml exec -T rabbitmq rabbitmqctl add_user "$RABBITMQ_USER" "$RABBITMQ_PASSWORD" >/dev/null 2>&1 || true
docker compose -f docker-compose.dev.yml exec -T rabbitmq rabbitmqctl set_permissions -p "$RABBITMQ_VHOST" "$RABBITMQ_USER" ".*" ".*" ".*" >/dev/null
docker compose -f docker-compose.dev.yml exec -T rabbitmq rabbitmqctl set_user_tags "$RABBITMQ_USER" administrator >/dev/null

echo "[bootstrap] Development dependencies are ready"
