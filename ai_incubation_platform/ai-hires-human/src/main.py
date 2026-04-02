"""
AI 雇佣真人平台 — 当 AI 无法独立完成（尤其真实世界交互）时，雇佣真人执行并回传结果。
"""
import os
import sys

# 支持从仓库根目录执行: PYTHONPATH=src python src/main.py
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI

from api.meta import router as meta_router
from api.payment import router as payment_router
from api.tasks import router as tasks_router

app = FastAPI(
    title="AI Hires Human",
    description=(
        "AI 因能力边界（线下到场、物理操作、合规人工判断等）发布任务，"
        "真人接单、交付，由 AI 雇主验收；默认创建即可接单。"
    ),
    version="0.4.0",
)

app.include_router(tasks_router)
app.include_router(meta_router)
app.include_router(payment_router)


@app.get("/")
async def root():
    return {
        "message": "AI 雇佣真人平台",
        "vision": (
            "当 AI 要做一件事但做不到时（与真实世界交互、需肉身或人工签核），"
            "通过本平台雇佣真人完成，并把交付结果回传给上游 AI / Agent。"
        ),
        "status": "running",
        "version": "0.4.0",
        "endpoints": {
            "tasks": "/api/tasks",
            "task_search": "/api/tasks/search",
            "payment": "/api/payment",
            "agent_tools": "/api/meta/agent-tools",
            "docs": "/docs",
        },
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8004)
