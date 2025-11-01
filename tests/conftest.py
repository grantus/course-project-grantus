import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.middleware.auth import make_jwt  # noqa: E402
from app.utils.db import init_db  # noqa: E402

os.environ.setdefault("VAULT_ADDR", "http://localhost:8200")
os.environ.setdefault("VAULT_TOKEN", "root")


@pytest.fixture(scope="session", autouse=True)
def _init_db():
    os.environ.setdefault("DB_DSN", "postgresql://app:app@db:5432/app")
    init_db()


make_jwt = make_jwt
