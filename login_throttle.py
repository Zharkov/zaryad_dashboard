import threading
import time

MAX_ATTEMPTS = 5
WINDOW_SECONDS = 300
_FAILS: dict[str, list[float]] = {}
_LOCK = threading.Lock()


def is_locked(username: str) -> bool:
    now = time.time()
    with _LOCK:
        attempts = [t for t in _FAILS.get(username, []) if now - t < WINDOW_SECONDS]
        _FAILS[username] = attempts
        return len(attempts) >= MAX_ATTEMPTS


def register_failure(username: str) -> None:
    with _LOCK:
        _FAILS.setdefault(username, []).append(time.time())


def register_success(username: str) -> None:
    with _LOCK:
        _FAILS.pop(username, None)
