from __future__ import annotations

import time
from functools import wraps
from typing import Any, Callable, Awaitable, Dict, List

from fastapi import HTTPException, Request, status

bucket: Dict[str, List[float]] = {}


def _get_request_from_args_kwargs(args, kwargs) -> Request | None:
    req = kwargs.get("request")
    if isinstance(req, Request):
        return req

    for arg in args:
        if isinstance(arg, Request):
            return arg
    return None


def rate_limit(limit: int, period: int):
    def decorator(func: Callable[..., Awaitable[Any]]):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            request = _get_request_from_args_kwargs(args, kwargs)
            if request is None:
                return await func(*args, **kwargs)

            key = request.client.host
            now = time.time()

            timestamps = bucket.get(key, [])
            timestamps = [t for t in timestamps if now - t < period]

            if len(timestamps) >= limit:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Rate limit exceeded",
                )

            timestamps.append(now)
            if timestamps:
                bucket[key] = timestamps
            else:
                bucket.pop(key, None)

            return await func(*args, **kwargs)

        return wrapper

    return decorator