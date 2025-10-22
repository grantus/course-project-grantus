import datetime
import json
import logging

logger = logging.getLogger("audit")
handler = logging.StreamHandler()
formatter = logging.Formatter("%(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)


def audit_log(request, user_id: str, action: str, outcome: str):
    entry = {
        "ts": datetime.datetime.now(datetime.UTC).isoformat(timespec="seconds") + "Z",
        "actor": user_id or "anonymous",
        "method": request.method,
        "path": request.url.path,
        "action": action,
        "outcome": outcome,
    }
    logger.info(json.dumps(entry, ensure_ascii=False))
