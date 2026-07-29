"""Shared Redis rate limiter with deterministic in-process fallback."""
from __future__ import annotations
import threading, time

class RateLimiter:
    def __init__(self, redis_url: str = "", namespace: str = "veraxis"):
        self.namespace=namespace; self._local={}; self._lock=threading.Lock(); self.redis=None
        if redis_url:
            try:
                from redis import Redis
                self.redis=Redis.from_url(redis_url, socket_connect_timeout=1, socket_timeout=1)
                self.redis.ping()
            except Exception:
                self.redis=None

    def limited(self, scope: str, subject: str, limit: int, window_seconds: int=60) -> bool:
        key=f"{self.namespace}:rate:{scope}:{subject}"
        if self.redis is not None:
            try:
                pipe=self.redis.pipeline(); pipe.incr(key); pipe.ttl(key); count,ttl=pipe.execute()
                if ttl < 0: self.redis.expire(key,window_seconds)
                return int(count)>int(limit)
            except Exception:
                pass
        now=time.monotonic()
        with self._lock:
            recent=[stamp for stamp in self._local.get(key,[]) if now-stamp<window_seconds]
            if len(recent)>=limit: self._local[key]=recent; return True
            recent.append(now); self._local[key]=recent; return False
