# AI Assistant Log - Smart Task Planner

## История ключевых промптов и взаимодействий с AI

### Этап 1: Проектирование структуры проекта

**Промпт:** Спроектируй структуру папок и файлов для бэкенда приложения 'Умный планировщик задач' (Smart Task Planner) на стеке Python FastAPI + SQLAlchemy + Pydantic.
Требования к функционалу
Пользователи: Регистрация, аутентификация (JWT), профиль.
Задачи: CRUD (создание, чтение, обновление, удаление). У задачи должны быть поля: заголовок, описание, статус (новая, в работе, выполнена), дедлайн, приоритет, ссылка на пользователя (владелец).
ИИ-функция: Эндпоинт, который принимает описание задачи, а сервис (пока заглушка) должен предлагать разбить её на подзадачи или оценить время выполнения.

**Ответ AI:** Предложил структуру с папками `core/`, `models/`, `schemas/`, `api/`, `services/`, файлы `database.py`, `security.py`, `config.py`. Подробное описание каждого компонента.

---

### Этап 2: Настройка базы данных и моделей

**Промпт:** Напиши код для database.py (подключение к БД, сессия, базовый класс) и models.py (модели User и Task для SQLAlchemy) согласно спроектированной структуре.

**Ответ AI:** Предоставил код с использованием SQLAlchemy, включая настройку engine, sessionmaker, declarative_base. Модели User и Task с полями и связями.

**Проблема:** Возникла ошибка `ValueError: password cannot be longer than 72 bytes` при хешировании паролей.

**Решение:** ```python def get_password_hash(password: str) -> str:
    """Хеширование пароля с поддержкой длинных паролей"""
    password_bytes = password.encode('utf-8')
    if len(password_bytes) > 72:
        password_bytes = hashlib.sha256(password_bytes).hexdigest().encode('utf-8')
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')


### Этап 3: Реализация JWT аутентификации

**Промпт:** Реализуй JWT аутентификацию: функции создания токена, верификации, зависимости для получения текущего пользователя.

**Ответ AI:** Создал функции create_access_token, verify_password, get_password_hash в security.py. Добавил эндпоинты /auth/register и /auth/login с использованием OAuth2PasswordBearer.

**Проблема:** Ошибка 422 Unprocessable Entity при регистрации из-за несоответствия версий Pydantic.

**Решение:** Адаптировал код для Pydantic 1.x:
class Config:
    orm_mode = True  # вместо from_attributes
obj.dict()  # вместо obj.model_dump()

### Этап 4: Интеграция AI-функций 

**Промпт:** Создай сервис ai_service.py с заглушками для категоризации и оценки времени. Используй простые правила на основе ключевых слов.

**Ответ AI:** 
def _get_mock_category(self, description: str) -> TaskCategoryEnum:
    description_lower = description.lower()
    if "работ" in description_lower:
        return TaskCategoryEnum.WORK
    # ... остальные правила

### Этап 5: Тестирование и отладка

**Промпт:** Почему возникает ошибка AttributeError: module 'datetime' has no attribute 'utcnow'?

**Ответ AI:** Объяснил, что в Python 3.12+ метод utcnow() удален. Предложил замену:
from datetime import datetime, timezone
timestamp = datetime.now(timezone.utc).isoformat()
# или просто
timestamp = datetime.now().isoformat()

### Этап 6: Продвинутая обработка ошибок AI API

**Промпт:** Добавь в ai_service.py улучшенную обработку ошибок с повторными попытками, параллельными запросами и graceful degradation.

**Ответ AI:**
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((httpx.TimeoutException, httpx.HTTPStatusError))
)
async def _call_ai_api(self, prompt: str) -> Optional[str]:
    # реализация

async def analyze_task(self, description: str) -> Dict:
    category_task = self.categorize_task(description)
    time_task = self.estimate_time(description)
    category, time = await asyncio.gather(category_task, time_task, return_exceptions=True)

### Этап 7: Unit-тесты

**Промпт:** Напиши unit-тесты для функции парсинга ответа ИИ по категории и для роута создания задачи.

**Ответ AI:**
@pytest.mark.asyncio
async def test_categorize_task_work_keywords(ai_service):
    description = "Подготовить отчет для клиента"
    category = await ai_service.categorize_task(description)
    assert category == TaskCategoryEnum.WORK

def test_create_task_success(test_user):
    response = client.post("/tasks/", json=task_data, headers=headers)
    assert response.status_code == 201

### Этап 8: Документация и README

**Промпт:** Сгенерируй README.md файл для проекта с описанием установки, API эндпоинтов, примерами использования.

**Ответ AI:** Создал структурированный README с разделами:
Описание проекта
Технологии
Установка и запуск
API эндпоинты
Примеры запросов
Структура проекта
Тестирование
AI Assistant Log
