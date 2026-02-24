from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import schemas  # models заменяем на schemas
from app.database import get_db
from app.routers.auth import get_current_user
# from app.models import User  ← УДАЛИТЬ эту строку
from app.services.ai_service import ai_service

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/categorize", response_model=schemas.TaskCategoryEnum)
async def categorize_task(
    request: schemas.AIAnalysisRequest,
    current_user: schemas.User = Depends(get_current_user),  # Здесь тоже schemas.User
    db: Session = Depends(get_db)
):
    """
    Определение категории задачи на основе описания
    Возвращает: работа, личное, здоровье, обучение, другое
    """
    if not request.task_description or len(request.task_description.strip()) < 5:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Task description must be at least 5 characters long"
        )

    category = await ai_service.categorize_task(request.task_description)
    return category


@router.post("/estimate-time", response_model=int)
async def estimate_time(
    request: schemas.AIAnalysisRequest,
    current_user: schemas.User = Depends(get_current_user),  # Здесь тоже schemas.User
    db: Session = Depends(get_db)
):
    """
    Оценка времени выполнения задачи в минутах
    """
    if not request.task_description or len(request.task_description.strip()) < 5:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Task description must be at least 5 characters long"
        )

    minutes = await ai_service.estimate_time(request.task_description)
    return minutes


@router.post("/analyze", response_model=schemas.AIAnalysisResponse)
async def analyze_task(
    request: schemas.AIAnalysisRequest,
    current_user: schemas.User = Depends(get_current_user),  # Здесь тоже schemas.User
    db: Session = Depends(get_db)
):
    """
    Комплексный анализ задачи:
    - категория
    - оценка времени
    - подзадачи
    - предложенный приоритет
    - советы
    """
    if not request.task_description or len(request.task_description.strip()) < 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Task description must be at least 10 characters long"
        )

    result = await ai_service.analyze_task(
        description=request.task_description,  # Измените на description
        title=request.task_title  # Измените на title
    )

    return result