from fastapi import FastAPI
from app.config.settings import settings

app = FastAPI(title=settings.app_name)

@app.get("/health")
async def health_check():
    return {"status": "healthy", "environment": settings.environment}

