from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional, List
from enum import Enum

from sqlalchemy import Column, Integer, String, DateTime, Text, Enum as SQLEnum, ForeignKey, Boolean
from sqlalchemy.orm import relationship

from app.database import Base


# ---------- Перечисления ----------
class TaskStatusEnum(str, Enum):
    NEW = "новая"
    IN_PROGRESS = "в работе"
    DONE = "выполнена"


class TaskPriorityEnum(str, Enum):
    LOW = "низкий"
    MEDIUM = "средний"
    HIGH = "высокий"


class TaskCategoryEnum(str, Enum):  # НОВОЕ
    WORK = "работа"
    PERSONAL = "личное"
    HEALTH = "здоровье"
    LEARNING = "обучение"
    OTHER = "другое"


# ---------- SQLAlchemy модели ----------
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    is_active = Column(Boolean, default=True)
    tasks = relationship("Task", back_populates="owner", cascade="all, delete-orphan")


class Task(Base):
    __tablename__ = "tasks"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True, nullable=False)
    description = Column(Text, nullable=True)
    status = Column(SQLEnum(TaskStatusEnum), default=TaskStatusEnum.NEW, nullable=False)
    priority = Column(SQLEnum(TaskPriorityEnum), default=TaskPriorityEnum.MEDIUM, nullable=False)
    category = Column(SQLEnum(TaskCategoryEnum), default=TaskCategoryEnum.OTHER, nullable=False)  # НОВОЕ
    estimated_time = Column(Integer, nullable=True)  # НОВОЕ (в минутах)
    deadline = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    owner = relationship("User", back_populates="tasks")


# ---------- Pydantic схемы для пользователей ----------
class UserBase(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    full_name: Optional[str] = Field(None, max_length=100)


class UserCreate(UserBase):
    password: str = Field(..., min_length=6)


class UserResponse(UserBase):
    id: int
    created_at: datetime
    is_active: bool

    class Config:
        orm_mode = True


# ---------- Схемы для токенов ----------
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    username: Optional[str] = None


# ---------- Схемы для задач ----------
class TaskBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    status: TaskStatusEnum = TaskStatusEnum.NEW
    priority: TaskPriorityEnum = TaskPriorityEnum.MEDIUM
    category: TaskCategoryEnum = TaskCategoryEnum.OTHER  # НОВОЕ
    estimated_time: Optional[int] = Field(None, ge=1, le=1440)  # НОВОЕ (1-1440 минут)
    deadline: Optional[datetime] = None


class TaskCreate(TaskBase):
    pass


class TaskUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    status: Optional[TaskStatusEnum] = None
    priority: Optional[TaskPriorityEnum] = None
    category: Optional[TaskCategoryEnum] = None  # НОВОЕ
    estimated_time: Optional[int] = Field(None, ge=1, le=1440)  # НОВОЕ
    deadline: Optional[datetime] = None


class TaskResponse(TaskBase):
    id: int
    created_at: datetime
    updated_at: datetime
    owner_id: int

    class Config:
        orm_mode = True


# ---------- Схемы для AI ----------
class AIAnalysisRequest(BaseModel):
    task_description: str = Field(..., min_length=10, max_length=2000)
    task_title: Optional[str] = Field(None, max_length=200)


class AIAnalysisResponse(BaseModel):
    category: TaskCategoryEnum  # НОВОЕ
    estimated_time: int  # НОВОЕ (в минутах)
    subtasks: List[str]
    suggested_priority: TaskPriorityEnum
    tips: Optional[List[str]] = None