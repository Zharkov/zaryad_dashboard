import json
from utils import now_msk


def audit(c, action: str, shift_id: int | None, details: dict, user: str) -> None:
    details_with_user = {**details, "by": user, "via": "web"}
    c.execute(
        "INSERT INTO audit_log (ts, action, shift_id, details) VALUES (?, ?, ?, ?)",
        (now_msk().isoformat(), action, shift_id,
         json.dumps(details_with_user, ensure_ascii=False)),
    )
