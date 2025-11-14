import os
import time
from typing import Optional

import hvac

MOUNT_POINT = "kv"
SECRET_PATH = "jwt"
SECRET_KEY = "JWT_SECRET"
RETRY_SECONDS = 30
SLEEP_STEP = 1


def _read_from_vault(client: hvac.Client) -> str:
    res = client.secrets.kv.v2.read_secret_version(
        mount_point=MOUNT_POINT,
        path=SECRET_PATH,
        raise_on_deleted_version=True,
    )
    data = res["data"]["data"]
    if SECRET_KEY not in data or not data[SECRET_KEY]:
        raise RuntimeError(
            f"Secret key '{SECRET_KEY}' missing at {MOUNT_POINT}/{SECRET_PATH}"
        )
    return data[SECRET_KEY]


def get_jwt_secret() -> str:
    env_secret = os.getenv(SECRET_KEY)
    if env_secret:
        return env_secret

    vault_addr = os.getenv("VAULT_ADDR")
    vault_token = os.getenv("VAULT_TOKEN")
    if not vault_addr:
        raise RuntimeError(
            "Missing VAULT_ADDR (required to fetch JWT secret from Vault)"
        )
    if not vault_token:
        raise RuntimeError(
            "Missing VAULT_TOKEN (required to fetch JWT secret from Vault)"
        )

    client = hvac.Client(url=vault_addr, token=vault_token)

    deadline = time.time() + RETRY_SECONDS
    last_err: Optional[Exception] = None
    while time.time() < deadline:
        try:
            if not client.is_authenticated():
                raise RuntimeError("Not authenticated to Vault (bad token?)")
            return _read_from_vault(client)
        except Exception as err:
            last_err = err
            time.sleep(SLEEP_STEP)

    raise RuntimeError(
        f"Failed to read {MOUNT_POINT}/{SECRET_PATH} from Vault: {last_err}"
    )
