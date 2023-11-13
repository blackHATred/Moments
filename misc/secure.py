import itsdangerous
from passlib.context import CryptContext

try:
    from config import TOKEN_SECRET_KEY
except ModuleNotFoundError:
    from config_example import TOKEN_SECRET_KEY

# Эта штука под капотом даже автоматически генерирует соль
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
token_generator = itsdangerous.URLSafeSerializer(TOKEN_SECRET_KEY)


def crypt(string: str) -> str:
    """
    Хэширует строку
    :param string: пароль или иная строка
    :return: хэш пароля
    """
    return pwd_context.hash(string)


def verify(string: str, hashed: str) -> bool:
    """
    Сверяет хэш строки с данным хэшом
    :param string: строка, для которой проверяем хэш
    :param hashed: сверяемый хэш
    :return: True/False
    """
    return pwd_context.verify(string, hashed)

