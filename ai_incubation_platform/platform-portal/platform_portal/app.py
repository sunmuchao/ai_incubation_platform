"""
静态 HTML 文档门户：将原工作区根目录下的项目介绍页统一由 Python 提供。
"""
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

_STATIC = Path(__file__).resolve().parent / "static"

app = FastAPI(
    title="AI Incubation Platform — 文档门户",
    description="可视化项目导航与各子项目介绍页（原独立 HTML，现由本服务托管）",
    version="0.1.0",
)


@app.get("/api/health")
async def health() -> dict:
    return {"status": "ok", "service": "platform-portal"}


# 静态站点；根路径由 static/index.html 跳转至导航页
app.mount(
    "/",
    StaticFiles(directory=str(_STATIC), html=True),
    name="site",
)
