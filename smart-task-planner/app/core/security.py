from datetime import datetime, timedelta
from typing import Union, Any
import hashlib
import bcrypt as bcrypt_lib  # используем прямой импорт bcrypt

from jose import jwt
from app.core.config import settings


def get_password_hash(password: str) -> str:
    """
    Хеширование пароля с использованием прямого bcrypt
    """
    # Преобразуем пароль в байты
    password_bytes = password.encode('utf-8')

    # Если пароль длиннее 72 байт, хешируем его через SHA256
    if len(password_bytes) > 72:
        password_bytes = hashlib.sha256(password_bytes).hexdigest().encode('utf-8')

    # Генерируем соль и хеш
    salt = bcrypt_lib.gensalt()
    hashed = bcrypt_lib.hashpw(password_bytes, salt)

    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Проверка пароля
    """
    # Преобразуем пароль в байты
    password_bytes = plain_password.encode('utf-8')
    hashed_bytes = hashed_password.encode('utf-8')

    # Если пароль длиннее 72 байт, хешируем через SHA256
    if len(password_bytes) > 72:
        password_bytes = hashlib.sha256(password_bytes).hexdigest().encode('utf-8')

    # Проверяем
    return bcrypt_lib.checkpw(password_bytes, hashed_bytes)


def create_access_token(subject: Union[str, Any]) -> str:
    """Создание JWT токена"""
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt