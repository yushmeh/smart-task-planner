from pydantic_settings import BaseSettings
from typing import List, Optional


class Settings(BaseSettings):
    # База данных
    DATABASE_URL: str = "sqlite:///./smart_planner.db"

    # JWT настройки
    SECRET_KEY: str = "your-secret-key-change-in-production-12345"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # CORS
    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000"]

    # Настройки приложения
    PROJECT_NAME: str = "Smart Task Planner"
    VERSION: str = "1.0.0"
    DEBUG: bool = True

    # AI API настройки (OpenAI или совместимые)
    AI_API_KEY: Optional[str] = None  # Можно оставить пустым для заглушки
    AI_API_URL: str = "https://api.openai.com/v1/chat/completions"  # Для OpenAI
    AI_MODEL: str = "gpt-3.5-turbo"  # или "deepseek-chat", "yandexgpt-lite" и т.д.

    # Альтернатива: использовать DeepSeek (бесплатно)
    # AI_API_URL: str = "https://api.deepseek.com/v1/chat/completions"
    # AI_MODEL: str = "deepseek-chat"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()