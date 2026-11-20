import hashlib
import secrets
from collections import OrderedDict, deque
from ipaddress import ip_address
from threading import Lock
from time import monotonic

from fastapi import HTTPException, Request

from app.core.config import settings


def new_token() -> str:
    return secrets.token_urlsafe(32)


def digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def read_bearer(value: str | None) -> str | None:
    if value is None:
        return None
    scheme, _, token = value.partition(" ")
    if scheme.lower() != "bearer" or not 1 <= len(token) <= 128 or not token.isascii():
        raise HTTPException(401, "Your guest session is invalid.")
    return token


class RateLimiter:
    def __init__(self):
        self.history: OrderedDict[tuple[str, str], deque[float]] = OrderedDict()
        self.lock = Lock()

    def check(self, action: str, identity: str, limit: int):
        now = monotonic()
        key = (action, identity)
        with self.lock:
            while self.history:
                oldest, entries = next(iter(self.history.items()))
                if entries[-1] > now - 60 and len(self.history) < 10000:
                    break
                self.history.pop(oldest)
            hits = self.history.setdefault(key, deque())
            while hits and hits[0] <= now - 60:
                hits.popleft()
            if len(hits) >= limit:
                raise HTTPException(429, "Too many requests. Try again in a minute.", headers={"Retry-After": "60"})
            hits.append(now)
            self.history.move_to_end(key)


def client_ip(request: Request) -> str:
    header = settings().rate_limit_client_ip_header
    forwarded = request.headers.get(header) if header else None
    if forwarded:
        try:
            return str(ip_address(forwarded.strip()))
        except ValueError:
            pass
    return request.client.host if request.client else "unknown"
