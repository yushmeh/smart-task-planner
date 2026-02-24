from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app import schemas
from app.database import get_db
from app.routers.auth import get_current_user
from app.services.ai_service import ai_service

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.post("/", response_model=schemas.TaskResponse, status_code=201)
async def create_task(
        task_data: schemas.TaskCreate,
        db: Session = Depends(get_db),
        current_user: schemas.User = Depends(get_current_user)
):
    """Создание новой задачи с AI-анализом"""

    # Если категория не указана, определяем через AI
    if task_data.category == schemas.TaskCategoryEnum.OTHER and task_data.description:
        try:
            category = await ai_service.categorize_task(task_data.description)
            task_data.category = category
        except Exception as e:
            # Если AI не сработал, оставляем OTHER
            pass

    # Если время не указано, оцениваем через AI
    if not task_data.estimated_time and task_data.description:
        try:
            estimated_time = await ai_service.estimate_time(task_data.description)
            task_data.estimated_time = estimated_time
        except Exception as e:
            # Если AI не сработал, оставляем None
            pass

    # Создаём задачу
    db_task = schemas.Task(
        **task_data.dict(),
        owner_id=current_user.id
    )

    db.add(db_task)
    db.commit()
    db.refresh(db_task)

    return db_task


@router.get("/", response_model=List[schemas.TaskResponse])
def read_tasks(
        skip: int = Query(0, ge=0),
        limit: int = Query(100, ge=1, le=100),
        status: Optional[schemas.TaskStatusEnum] = None,
        category: Optional[schemas.TaskCategoryEnum] = None,  # НОВЫЙ ФИЛЬТР
        db: Session = Depends(get_db),
        current_user: schemas.User = Depends(get_current_user)
):
    """Получение списка задач текущего пользователя"""

    query = db.query(schemas.Task).filter(schemas.Task.owner_id == current_user.id)

    if status:
        query = query.filter(schemas.Task.status == status)

    if category:  # НОВЫЙ ФИЛЬТР
        query = query.filter(schemas.Task.category == category)

    tasks = query.offset(skip).limit(limit).all()
    return tasks


@router.get("/{task_id}", response_model=schemas.TaskResponse)
def read_task(
        task_id: int,
        db: Session = Depends(get_db),
        current_user: schemas.User = Depends(get_current_user)
):
    """Получение задачи по ID"""

    task = db.query(schemas.Task).filter(
        schemas.Task.id == task_id,
        schemas.Task.owner_id == current_user.id
    ).first()

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    return task


@router.put("/{task_id}", response_model=schemas.TaskResponse)
def update_task(
        task_id: int,
        task_data: schemas.TaskUpdate,
        db: Session = Depends(get_db),
        current_user: schemas.User = Depends(get_current_user)
):
    """Обновление задачи"""

    task = db.query(schemas.Task).filter(
        schemas.Task.id == task_id,
        schemas.Task.owner_id == current_user.id
    ).first()

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    update_data = task_data.dict(exclude_unset=True)

    for field, value in update_data.items():
        setattr(task, field, value)

    db.commit()
    db.refresh(task)

    return task


@router.delete("/{task_id}", status_code=204)
def delete_task(
        task_id: int,
        db: Session = Depends(get_db),
        current_user: schemas.User = Depends(get_current_user)
):
    """Удаление задачи"""

    task = db.query(schemas.Task).filter(
        schemas.Task.id == task_id,
        schemas.Task.owner_id == current_user.id
    ).first()

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    db.delete(task)
    db.commit()

    return None