from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime  # правильный импорт

from app.core.config import settings
from app.database import engine
from app import schemas
from app.routers import auth_router, tasks_router, ai_router

# Создание таблиц
schemas.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    debug=settings.DEBUG,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключение роутеров
app.include_router(auth_router)
app.include_router(tasks_router)
app.include_router(ai_router)


@app.get("/")
async def root():
    return {
        "message": f"Welcome to {settings.PROJECT_NAME} API",
        "version": settings.VERSION,
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "database": "connected",
        "timestamp": datetime.now().isoformat()  # Самый простой вариант
    }