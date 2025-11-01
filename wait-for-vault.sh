#!/bin/sh
set -e

echo "Waiting for Vault to be ready..."
until curl -sf -H "X-Vault-Token: $VAULT_TOKEN" "$VAULT_ADDR/v1/sys/health" > /dev/null; do
  sleep 1
done

echo "Vault is ready, starting app..."
exec "$@"
