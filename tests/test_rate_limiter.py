from services.platform.rate_limiter import RateLimiter

def test_local_rate_limiter_blocks_after_limit():
    limiter=RateLimiter("")
    assert limiter.limited("login","ip",2) is False
    assert limiter.limited("login","ip",2) is False
    assert limiter.limited("login","ip",2) is True
    assert limiter.limited("login","other",2) is False
