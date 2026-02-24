# AI Assistant Log - Smart Task Planner

## История ключевых промптов и взаимодействий с AI

### Этап 1: Проектирование структуры проекта

**Промпт:** Спроектируй структуру папок и файлов для бэкенда приложения 'Умный планировщик задач' (Smart Task Planner) на стеке Python FastAPI + SQLAlchemy + Pydantic.
Требования к функционалу
Пользователи: Регистрация, аутентификация (JWT), профиль.
Задачи: CRUD (создание, чтение, обновление, удаление). У задачи должны быть поля: заголовок, описание, статус (новая, в работе, выполнена), дедлайн, приоритет, ссылка на пользователя (владелец).
ИИ-функция: Эндпоинт, который принимает описание задачи, а сервис (пока заглушка) должен предлагать разбить её на подзадачи или оценить время выполнения.

**Ответ AI:** Предложил структуру с папками `core/`, `models/`, `schemas/`, `api/`, `services/`, файлы `database.py`, `security.py`, `config.py`. Подробное описание каждого компонента.

**Проблема:** Возникла ошибка `ValueError: password cannot be longer than 72 bytes` при хешировании паролей.

**Решение:** 
```python
def get_password_hash(password: str) -> str:
    """Хеширование пароля с поддержкой длинных паролей"""
    password_bytes = password.encode('utf-8')
    if len(password_bytes) > 72:
        password_bytes = hashlib.sha256(password_bytes).hexdigest().encode('utf-8')
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')
```

**Промпт:** Реализуй JWT аутентификацию: функции создания токена, верификации, зависимости для получения текущего пользователя.

**Ответ AI:** Создал функции create_access_token, verify_password, get_password_hash в security.py. Добавил эндпоинты /auth/register и /auth/login с использованием OAuth2PasswordBearer.

**Проблема:** Ошибка 422 Unprocessable Entity при регистрации из-за несоответствия версий Pydantic.

**Решение:** Адаптировал код для Pydantic 1.x:
```python
class Config:
    orm_mode = True  # вместо from_attributes
obj.dict()  # вместо obj.model_dump()
```

---

### Этап 2: Реализация "Умных" функций с помощью AI API

**Промпт:** Запрос на обновление кода для интеграции AI-функций.

**Ответ AI:** ИИ сгенерировал код для ai_service.py с функциями:
- Автоматическая категоризация задач (работа, личное, здоровье, обучение, другое)
- Оценка времени выполнения в минутах
- Комплексный анализ задачи

---

### Этап 3: Генерация тестов и документации

**Промпт:** Напиши unit-тесты (используя pytest) для:
- Функции парсинга ответа ИИ по категории.
- Роута создания задачи.
Также сгенерируй README.md файл для проекта с описанием установки, API эндпоинтов, примерами использования.

**Ответ AI:** Тесты для test_ai_parsing.py и test_tasks.py, создал структурированный README с разделами:

- **Описание проекта** — цель и возможности
- **Технологии** — стек разработки
- **Установка и запуск** — пошаговая инструкция
- **API эндпоинты** — все доступные маршруты
- **Примеры запросов** — curl команды
- **Структура проекта** — дерево папок
- **Тестирование** — запуск тестов

**Проблема:** Почему возникает ошибка AttributeError: module 'datetime' has no attribute 'utcnow'?

**Ответ AI:** Объяснил, что в Python 3.12+ метод utcnow() удален. Предложил замену:
```python
from datetime import datetime, timezone
timestamp = datetime.now(timezone.utc).isoformat()
# или просто
timestamp = datetime.now().isoformat()
```

---

### Этап 4: Рефакторинг и оптимизация (Code Review от ИИ)

**Промпт:** Проведи рефакторинг этого кода. Предложи улучшения для читаемости, производительности и соответствия лучшим практикам. Особое внимание удели обработке ошибок при вызове внешнего AI API.

**Ответ AI:** 
1. Улучшенная обработка ошибок AI API с повторными попытками
```python
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((httpx.TimeoutException, httpx.HTTPStatusError)),
    before_sleep=before_sleep_log(logger, logging.WARNING)
)
async def _call_ai_api(self, prompt: str, max_tokens: int = 50) -> Optional[str]:
    # Отправка запроса к AI API с автоматическими повторными попытками
```

Польза: Автоматические повторные попытки при временных ошибках сети или таймаутах, экспоненциальная задержка между попытками.

2. Параллельные запросы к AI API в analyze_task
```python
async def analyze_task(self, description: str, title: Optional[str] = None) -> Dict[str, Any]:
    # Запускаем запросы параллельно
    category_task = self.categorize_task(description)
    time_task = self.estimate_time(description)
    
    # Ждем оба результата
    category, estimated_time = await asyncio.gather(
        category_task,
        time_task,
        return_exceptions=True
    )
```

Польза: Ускорение работы в 2 раза за счет параллельного выполнения запросов.

**Промпт:** Добавь в ai_service.py улучшенную обработку ошибок с повторными попытками, параллельными запросами и graceful degradation.

**Ответ AI:**
```python
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
```
