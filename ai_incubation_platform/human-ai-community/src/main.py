"""
人 AI 共建社区 - 主入口
"""
from fastapi import FastAPI
from api.community import router as community_router

app = FastAPI(
    title="Human-AI Community",
    description="人类和 AI 共建的社区平台",
    version="0.1.0"
)

# 注册路由
app.include_router(community_router)

@app.get("/")
async def root():
    return {
        "message": "欢迎使用人 AI 共建社区",
        "status": "running",
        "endpoints": {
            "members": "/api/members",
            "posts": "/api/posts",
            "comments": "/api/comments",
            "docs": "/docs"
        }
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8007)
