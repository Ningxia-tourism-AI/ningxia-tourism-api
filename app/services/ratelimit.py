"""极简内存限流：按客户端 IP 做滑动窗口计数。

用途是防止公网部署后被人刷 AI 接口消耗额度；
进程内存储，重启即清零，单实例部署足够。
"""
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request


class RateLimiter:
    def __init__(self, limit: int, window: int) -> None:
        self.limit = limit
        self.window = window
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def _client(self, request: Request) -> str:
        # Render / 反向代理会把真实 IP 放在 X-Forwarded-For 的第一段
        forwarded = request.headers.get("x-forwarded-for", "")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    def check(self, request: Request) -> None:
        now = time.time()
        key = self._client(request)
        hits = self._hits[key]

        while hits and now - hits[0] > self.window:
            hits.popleft()

        if len(hits) >= self.limit:
            wait = int(self.window - (now - hits[0])) + 1
            raise HTTPException(
                status_code=429,
                detail=f"请求过于频繁，请 {wait} 秒后再试。",
            )

        hits.append(now)

        # 顺手清理长期不活跃的 key，避免内存无限增长
        if len(self._hits) > 500:
            for k in [k for k, v in self._hits.items() if not v or now - v[-1] > self.window * 10]:
                self._hits.pop(k, None)


# AI 接口：每分钟 10 次
ai_limiter = RateLimiter(limit=10, window=60)
# 列表接口：每分钟 120 次（正常浏览够用）
list_limiter = RateLimiter(limit=120, window=60)


def rate_limit_ai(request: Request) -> None:
    ai_limiter.check(request)


def rate_limit_list(request: Request) -> None:
    list_limiter.check(request)
