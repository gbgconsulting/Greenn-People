"""Rate limiting via Django cache (Redis ou locmem) — sem dependência extra."""

from __future__ import annotations

from django.core.cache import cache


def get_client_ip(request) -> str:
    """IP do cliente; respeita ``X-Forwarded-For`` quando há proxy."""
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR') or 'unknown'


def is_over_limit(key: str, limit: int, period: int) -> bool:
    """True se a chave já atingiu o limite no período."""
    cache_key = f'rl:{key}'
    count = cache.get(cache_key, 0)
    return count >= limit


def increment(key: str, period: int) -> int:
    """Incrementa contador e retorna o valor atual."""
    cache_key = f'rl:{key}'
    if cache.add(cache_key, 1, period):
        return 1
    try:
        return cache.incr(cache_key)
    except ValueError:
        cache.set(cache_key, 1, period)
        return 1
