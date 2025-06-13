from typing import Optional

from fastapi import Request, status
from fastapi.responses import JSONResponse
from redis.asyncio import Redis
from starlette.middleware.base import BaseHTTPMiddleware

from src.auth.dependencies import get_settings


def get_redis_instance():
    return Redis(
        host="redis-13649.crce199.us-west-2-2.ec2.redns.redis-cloud.com",
        port=13649,
        decode_responses=True,
        username="default",
        password=get_settings().REDIS_PASSWORD,
    )


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, window_sec: int = 30, max_requests: int = 10):
        super().__init__(app)
        self.window_sec = window_sec
        self.max_requests = max_requests
        self.redis_instance = get_redis_instance()

    async def permit_request(self, key: str):
        if await self.redis_instance.setnx(key, self.max_requests):
            await self.redis_instance.expire(key, self.window_sec)
        cache_val: Optional[bytes] = await self.redis_instance.get(key)

        if cache_val is not None:
            requests_remaining = int(cache_val)
            if requests_remaining > 0:
                await self.redis_instance.decr(key)
                return True

        return False

    async def dispatch(self, request: Request, call_next):
        if not request.client:
            raise ValueError("Client IP not found")

        client_ip = request.client.host
        key = f"{client_ip}:RATELIMIT"

        if not await self.permit_request(key):
            time_to_wait = await self.redis_instance.ttl(key)
            retry_info = f" Retry after {int(time_to_wait)}" if time_to_wait is not None else ""
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS, content={"detail": f"Rate limit exceeded.{retry_info}"}
            )

        response = await call_next(request)
        return response
