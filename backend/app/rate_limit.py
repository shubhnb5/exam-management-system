"""Small in-memory brute-force guard for the student login and forgot-password
endpoints. In-memory is enough for this app's single backend process; it
resets on restart, which is acceptable for a throttle."""

import threading
import time

from fastapi import HTTPException, status


class FailureThrottle:
    def __init__(self, max_failures: int, window_seconds: int):
        self.max_failures = max_failures
        self.window_seconds = window_seconds
        self._failures: dict[str, list[float]] = {}
        self._lock = threading.Lock()

    def _recent(self, key: str, now: float) -> list[float]:
        recent = [t for t in self._failures.get(key, []) if now - t < self.window_seconds]
        if recent:
            self._failures[key] = recent
        else:
            self._failures.pop(key, None)
        return recent

    def check(self, key: str) -> None:
        """Raises 429 if `key` has too many recent failures."""
        now = time.monotonic()
        with self._lock:
            recent = self._recent(key, now)
            if len(recent) >= self.max_failures:
                wait_minutes = max(1, round((self.window_seconds - (now - recent[0])) / 60))
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Too many attempts. Please try again in {wait_minutes} minute(s).",
                )

    def record_failure(self, key: str) -> None:
        with self._lock:
            self._failures.setdefault(key, []).append(time.monotonic())

    def reset(self, key: str) -> None:
        with self._lock:
            self._failures.pop(key, None)


student_login_throttle = FailureThrottle(max_failures=5, window_seconds=15 * 60)
