import importlib
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import scenic

app = FastAPI(
    title="宁夏文旅 AI 服务",
    description="景区数据查询 + AI 问答",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "*"
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 景区数据（已实现）
app.include_router(scenic.router)


def _maybe_include(name: str, prefix: str, tag: str):
    """路由文件里有内容才挂载，空文件直接跳过，避免导入报错。"""
    path = os.path.join(os.path.dirname(__file__), "routers", f"{name}.py")
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        return False
    module = importlib.import_module(f".routers.{name}", __package__)
    router = getattr(module, "router", None)
    if router is None:
        return False
    app.include_router(router, prefix=prefix, tags=[tag])
    return True


# 预留模块：写好内容后自动挂载
for _name, _prefix, _tag in (
    ("chat", "/api/chat", "AI 问答"),
    ("dialect", "/api/dialect", "方言"),
    ("itinerary", "/api/itinerary", "行程"),
):
    _maybe_include(_name, _prefix, _tag)


@app.get("/health", tags=["系统"], summary="健康检查")
def health():
    return {"status": "ok"}
