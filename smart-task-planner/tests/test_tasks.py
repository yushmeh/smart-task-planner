import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta  # только datetime и timedelta, без timezone

from app.main import app
from app.database import Base, get_db
from app.core.security import get_password_hash
from app import schemas

# Создаем тестовую базу данных
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# Переопределяем зависимость get_db для использования тестовой БД
def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


@pytest.fixture
def test_db():
    """Создает тестовую базу данных и очищает после тестов"""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def test_user(test_db):
    """Создает тестового пользователя и возвращает токен"""
    user_data = {
        "email": "test@example.com",
        "username": "testuser",
        "password": "testpass123",
        "full_name": "Test User"
    }

    # Создаем пользователя напрямую в БД
    db = TestingSessionLocal()
    hashed_password = get_password_hash(user_data["password"])
    db_user = schemas.User(
        email=user_data["email"],
        username=user_data["username"],
        hashed_password=hashed_password,
        full_name=user_data["full_name"]
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    db.close()

    # Логинимся для получения токена
    response = client.post(
        "/auth/login",
        data={
            "username": user_data["username"],
            "password": user_data["password"]
        }
    )
    assert response.status_code == 200
    token = response.json()["access_token"]

    return {"token": token, "user": user_data}


def test_create_task_success(test_user):
    """Тест успешного создания задачи"""
    # Простое решение - используем datetime.now() без timezone
    deadline = (datetime.now() + timedelta(days=1)).isoformat()

    task_data = {
        "title": "Тестовая задача",
        "description": "Описание тестовой задачи",
        "priority": "средний",
        "deadline": deadline
    }

    response = client.post(
        "/tasks/",
        json=task_data,
        headers={"Authorization": f"Bearer {test_user['token']}"}
    )

    assert response.status_code == 201
    data = response.json()
    assert data["title"] == task_data["title"]
    assert data["description"] == task_data["description"]
    assert data["priority"] == task_data["priority"]
    assert "id" in data
    assert "created_at" in data
    assert "owner_id" in data


def test_create_task_without_auth():
    """Тест создания задачи без авторизации"""
    task_data = {
        "title": "Тестовая задача",
        "description": "Описание тестовой задачи"
    }

    response = client.post("/tasks/", json=task_data)
    assert response.status_code == 401


def test_create_task_minimal_fields(test_user):
    """Тест создания задачи только с обязательными полями"""
    task_data = {
        "title": "Минимальная задача"
    }

    response = client.post(
        "/tasks/",
        json=task_data,
        headers={"Authorization": f"Bearer {test_user['token']}"}
    )

    assert response.status_code == 201
    data = response.json()
    assert data["title"] == task_data["title"]
    assert data["description"] is None
    assert data["status"] == "новая"
    assert data["priority"] == "средний"
    assert data["category"] == "другое"


def test_create_task_invalid_priority(test_user):
    """Тест создания задачи с недопустимым приоритетом"""
    task_data = {
        "title": "Тестовая задача",
        "priority": "неправильный"
    }

    response = client.post(
        "/tasks/",
        json=task_data,
        headers={"Authorization": f"Bearer {test_user['token']}"}
    )

    assert response.status_code == 422


def test_get_tasks_list(test_user):
    """Тест получения списка задач"""
    # Создаем несколько задач
    for i in range(3):
        task_data = {"title": f"Задача {i}"}
        client.post(
            "/tasks/",
            json=task_data,
            headers={"Authorization": f"Bearer {test_user['token']}"}
        )

    response = client.get(
        "/tasks/",
        headers={"Authorization": f"Bearer {test_user['token']}"}
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3


def test_get_single_task(test_user):
    """Тест получения конкретной задачи"""
    task_data = {"title": "Задача для получения"}
    create_response = client.post(
        "/tasks/",
        json=task_data,
        headers={"Authorization": f"Bearer {test_user['token']}"}
    )
    task_id = create_response.json()["id"]

    response = client.get(
        f"/tasks/{task_id}",
        headers={"Authorization": f"Bearer {test_user['token']}"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == task_id
    assert data["title"] == task_data["title"]


def test_get_nonexistent_task(test_user):
    """Тест получения несуществующей задачи"""
    response = client.get(
        "/tasks/99999",
        headers={"Authorization": f"Bearer {test_user['token']}"}
    )

    assert response.status_code == 404


def test_update_task(test_user):
    """Тест обновления задачи"""
    task_data = {"title": "Старое название"}
    create_response = client.post(
        "/tasks/",
        json=task_data,
        headers={"Authorization": f"Bearer {test_user['token']}"}
    )
    task_id = create_response.json()["id"]

    update_data = {
        "title": "Новое название",
        "status": "в работе"
    }
    response = client.put(
        f"/tasks/{task_id}",
        json=update_data,
        headers={"Authorization": f"Bearer {test_user['token']}"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == task_id
    assert data["title"] == update_data["title"]
    assert data["status"] == update_data["status"]


def test_delete_task(test_user):
    """Тест удаления задачи"""
    task_data = {"title": "Задача для удаления"}
    create_response = client.post(
        "/tasks/",
        json=task_data,
        headers={"Authorization": f"Bearer {test_user['token']}"}
    )
    task_id = create_response.json()["id"]

    delete_response = client.delete(
        f"/tasks/{task_id}",
        headers={"Authorization": f"Bearer {test_user['token']}"}
    )
    assert delete_response.status_code == 204

    get_response = client.get(
        f"/tasks/{task_id}",
        headers={"Authorization": f"Bearer {test_user['token']}"}
    )
    assert get_response.status_code == 404


def test_cannot_access_other_user_task(test_user):
    """Тест: пользователь не может получить доступ к задаче другого пользователя"""
    task_data = {"title": "Чужая задача"}
    create_response = client.post(
        "/tasks/",
        json=task_data,
        headers={"Authorization": f"Bearer {test_user['token']}"}
    )
    task_id = create_response.json()["id"]

    # Создаем второго пользователя
    db = TestingSessionLocal()
    other_user = schemas.User(
        email="other@example.com",
        username="otheruser",
        hashed_password=get_password_hash("otherpass"),
        full_name="Other User"
    )
    db.add(other_user)
    db.commit()
    db.close()

    login_response = client.post(
        "/auth/login",
        data={"username": "otheruser", "password": "otherpass"}
    )
    other_token = login_response.json()["access_token"]

    response = client.get(
        f"/tasks/{task_id}",
        headers={"Authorization": f"Bearer {other_token}"}
    )

    assert response.status_code == 404