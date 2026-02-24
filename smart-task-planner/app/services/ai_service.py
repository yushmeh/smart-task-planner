import httpx
import json
import logging
import asyncio
from typing import Dict, Any, Optional
from fastapi import HTTPException
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)

from app.core.config import settings
from app.schemas import TaskCategoryEnum, TaskPriorityEnum

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AIQuotaExceededError(Exception):
    """Превышен лимит запросов или недостаточно средств"""
    pass


class AITimeoutError(Exception):
    """Таймаут при запросе к AI API"""
    pass


class AIService:
    def __init__(self):
        self.api_key = settings.AI_API_KEY
        self.api_url = settings.AI_API_URL
        self.model = settings.AI_MODEL
        self.use_mock = True  # ← ПРИНУДИТЕЛЬНО ВКЛЮЧИТЕ ЗАГЛУШКИ
        self.timeout = 15.0  # Таймаут в секундах
        self.max_retries = 3  # Максимальное количество попыток

        if self.use_mock:
            logger.warning("⚠️ Using mock responses.")
        else:
            logger.info(f"✅ AI Service initialized with model: {self.model}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(
            (httpx.TimeoutException, httpx.HTTPStatusError, AITimeoutError)
        ),
        before_sleep=before_sleep_log(logger, logging.WARNING)
    )
    async def _call_ai_api(self, prompt: str, max_tokens: int = 50) -> Optional[str]:
        """
        Отправка запроса к AI API с автоматическими повторными попытками

        Особенности:
        - До 3 повторных попыток при временных ошибках
        - Экспоненциальная задержка между попытками (2, 4, 8 сек)
        - Специфичная обработка разных типов ошибок
        - Подробное логирование
        """
        if self.use_mock:
            return None

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system",
                 "content": "You are a helpful task management assistant. Respond only with the requested information, no additional text."},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": max_tokens,
            "temperature": 0.3,
        }

        attempt = 1
        while attempt <= self.max_retries:
            try:
                logger.info(f"📡 AI API request (attempt {attempt}/{self.max_retries})")

                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(self.api_url, headers=headers, json=payload)

                    # Специфичная обработка HTTP ошибок
                    if response.status_code == 402:
                        logger.error("💳 Insufficient balance or quota exceeded")
                        raise AIQuotaExceededError("Insufficient AI API balance")

                    if response.status_code == 429:
                        logger.warning("⏳ Rate limit exceeded, retrying...")
                        if attempt < self.max_retries:
                            wait_time = 2 ** attempt  # 2, 4, 8 секунд
                            logger.info(f"⏱️ Waiting {wait_time}s before retry")
                            await asyncio.sleep(wait_time)
                            attempt += 1
                            continue

                    response.raise_for_status()

                    data = response.json()
                    # Обработка ответа для разных API
                    if "choices" in data:
                        if data["choices"][0].get("message"):
                            result = data["choices"][0]["message"]["content"].strip()
                            logger.info(f"✅ AI API response received: {result[:50]}...")
                            return result
                        elif data["choices"][0].get("text"):
                            result = data["choices"][0]["text"].strip()
                            logger.info(f"✅ AI API response received: {result[:50]}...")
                            return result

                    logger.error(f"❌ Unexpected API response format: {data}")
                    return None

            except httpx.TimeoutException as e:
                logger.error(f"⏱️ AI API timeout (attempt {attempt}): {e}")
                if attempt == self.max_retries:
                    raise AITimeoutError("AI service timeout after multiple retries")

            except httpx.HTTPStatusError as e:
                logger.error(f"🌐 AI API HTTP error (attempt {attempt}): {e.response.status_code}")
                if e.response.status_code >= 500 and attempt < self.max_retries:
                    # Серверные ошибки - можно повторить
                    wait_time = 2 ** attempt
                    logger.info(f"⏱️ Waiting {wait_time}s before retry")
                    await asyncio.sleep(wait_time)
                else:
                    # Клиентские ошибки (4xx) - повторять бесполезно
                    raise HTTPException(
                        status_code=502,
                        detail=f"AI service error: {e.response.status_code}"
                    )

            except Exception as e:
                logger.error(f"❌ AI API error (attempt {attempt}): {str(e)}")
                if attempt == self.max_retries:
                    raise HTTPException(status_code=500, detail="AI service unavailable")

            attempt += 1
            if attempt <= self.max_retries:
                wait_time = 2 ** attempt
                logger.info(f"⏱️ Waiting {wait_time}s before retry")
                await asyncio.sleep(wait_time)

        return None

    def _get_mock_category(self, description: str) -> TaskCategoryEnum:
        """Заглушка для категоризации"""
        description_lower = description.lower()

        # Расширенный список ключевых слов
        work_words = ["работ", "проект", "клиент", "отчет", "презентац", "бизнес", "офис", "совещан"]
        personal_words = ["личн", "семь", "друз", "хобби", "отдых", "развлек", "покупк"]
        health_words = ["спорт", "трен", "здоров", "врач", "больниц", "медиц", "упраж", "диет"]
        learning_words = ["учит", "курс", "книг", "лекц", "образов", "школ", "универ", "тренинг"]

        if any(word in description_lower for word in work_words):
            return TaskCategoryEnum.WORK
        elif any(word in description_lower for word in personal_words):
            return TaskCategoryEnum.PERSONAL
        elif any(word in description_lower for word in health_words):
            return TaskCategoryEnum.HEALTH
        elif any(word in description_lower for word in learning_words):
            return TaskCategoryEnum.LEARNING
        else:
            return TaskCategoryEnum.OTHER

    def _get_mock_estimated_time(self, description: str) -> int:
        """Заглушка для оценки времени с более точной логикой"""
        description_lower = description.lower()

        # Анализ ключевых слов для более точной оценки
        if any(word in description_lower for word in ["минут", "быстр", "срочн"]):
            return 15
        elif any(word in description_lower for word in ["час", "лекц", "встреч"]):
            return 60
        elif any(word in description_lower for word in ["полдня", "4 час", "нескольк час"]):
            return 240
        elif any(word in description_lower for word in ["день", "сутк"]):
            return 480
        elif any(word in description_lower for word in ["больш", "сложн", "проект", "диплом"]):
            return 120
        else:
            return 30

    async def categorize_task(self, description: str) -> TaskCategoryEnum:
        """
        Задача 1: Автокатегоризация
        Отправляет описание в AI и получает категорию
        """
        if self.use_mock:
            logger.info("🤖 Using mock categorization")
            return self._get_mock_category(description)

        prompt = f"""Task description: "{description}"

        Categorize this task into one of these categories: 
        - work (работа)
        - personal (личное)
        - health (здоровье)
        - learning (обучение)
        - other (другое)

        Return ONLY the category name in Russian, one word: работа, личное, здоровье, обучение, or другое."""

        try:
            response = await self._call_ai_api(prompt, max_tokens=10)

            if response:
                response = response.strip().lower()
                if "работ" in response:
                    return TaskCategoryEnum.WORK
                elif "личн" in response:
                    return TaskCategoryEnum.PERSONAL
                elif "здоров" in response:
                    return TaskCategoryEnum.HEALTH
                elif "обуч" in response:
                    return TaskCategoryEnum.LEARNING
                else:
                    return TaskCategoryEnum.OTHER

        except AIQuotaExceededError:
            logger.warning("⚠️ AI quota exceeded, using mock categorization")
        except AITimeoutError:
            logger.warning("⏱️ AI timeout, using mock categorization")
        except Exception as e:
            logger.error(f"❌ AI categorization failed: {e}, using mock")

        return self._get_mock_category(description)

    async def estimate_time(self, description: str) -> int:
        """
        Задача 2: Оценка времени
        Возвращает количество минут для выполнения задачи
        """
        if self.use_mock:
            logger.info("🤖 Using mock time estimation")
            return self._get_mock_estimated_time(description)

        prompt = f"""Task description: "{description}"

        Estimate how many minutes this task will take to complete. 
        Consider it's a daily task in a task planner.
        Return ONLY a number (integer), no text, no units."""

        try:
            response = await self._call_ai_api(prompt, max_tokens=5)

            if response:
                import re
                numbers = re.findall(r'\d+', response)
                if numbers:
                    minutes = int(numbers[0])
                    return max(1, min(minutes, 1440))

        except Exception as e:
            logger.error(f"❌ AI time estimation failed: {e}, using mock")

        return self._get_mock_estimated_time(description)

    async def analyze_task(self, description: str, title: Optional[str] = None) -> Dict[str, Any]:
        """
        Комплексный анализ задачи с параллельными запросами

        Args:
            description: Описание задачи
            title: Заголовок задачи (опционально)
        """
        # Объединяем заголовок и описание для более точного анализа
        full_text = f"{title}. {description}" if title else description

        # Запускаем запросы параллельно
        category_task = self.categorize_task(full_text)
        time_task = self.estimate_time(full_text)

        # Ждем оба результата
        category, estimated_time = await asyncio.gather(
            category_task,
            time_task,
            return_exceptions=True
        )

        # Обработка ошибок
        if isinstance(category, Exception):
            logger.warning(f"⚠️ Category task failed: {category}")
            category = self._get_mock_category(full_text)

        if isinstance(estimated_time, Exception):
            logger.warning(f"⚠️ Time estimation failed: {estimated_time}")
            estimated_time = self._get_mock_estimated_time(full_text)

        # Генерируем подзадачи на основе полного текста
        subtasks = self._generate_subtasks(full_text)

        # Определяем приоритет
        priority = self._determine_priority(estimated_time)

        return {
            "category": category,
            "estimated_time": estimated_time,
            "subtasks": subtasks[:3],
            "suggested_priority": priority,
            "tips": [
                f"⏱️ На выполнение уйдет примерно {estimated_time} минут",
                f"📂 Категория: {category.value}",
                "🎯 Начните с самого важного"
            ]
        }

    def _generate_subtasks(self, description: str) -> list:
        """Генерация подзадач на основе описания"""
        desc = description.lower()

        if "написать" in desc or "создать" in desc:
            return [
                "📝 Исследовать требования",
                "📋 Составить план",
                "✍️ Подготовить черновик",
                "👀 Сделать ревью"
            ]
        elif "встреча" in desc or "звонок" in desc:
            return [
                "📅 Подготовить повестку",
                "👥 Пригласить участников",
                "🎯 Провести встречу",
                "📝 Записать решения"
            ]
        else:
            return [
                "🚀 Начать работу",
                "⚙️ Выполнить основную часть",
                "✅ Проверить результат",
                "🏁 Завершить"
            ]

    def _determine_priority(self, minutes: int) -> TaskPriorityEnum:
        """Определение приоритета на основе времени"""
        if minutes <= 15:
            return TaskPriorityEnum.LOW
        elif minutes <= 60:
            return TaskPriorityEnum.MEDIUM
        else:
            return TaskPriorityEnum.HIGH


# Создаем экземпляр сервиса
ai_service = AIService()