"""
AI 社区团购 - 主入口
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI
from api.products import router as products_router
from api.recommendation import router as recommendation_router
from api.notification import router as notification_router
from config.database import Base, engine

# 创建数据库表
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="AI Community Buying",
    description="AI 驱动的社区团购平台",
    version="0.1.0"
)

# 注册路由
app.include_router(products_router)
app.include_router(recommendation_router)
app.include_router(notification_router)

@app.get("/")
async def root():
    return {
        "message": "欢迎使用 AI 社区团购平台",
        "status": "running",
        "version": "0.1.0",
        "endpoints": {
            "商品管理": "/api/products",
            "团购管理": "/api/groups",
            "订单管理": "/api/orders",
            "智能推荐": "/api/recommendation",
            "通知服务": "/api/notifications",
            "接口文档": "/docs",
            "健康检查": "/health"
        }
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8005)
