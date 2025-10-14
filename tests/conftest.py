import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.middleware.auth import make_jwt  # noqa: E402

make_jwt = make_jwt
