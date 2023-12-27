import itsdangerous
from passlib.hash import pbkdf2_sha256

try:
    from config import TOKEN_SECRET_KEY
except ModuleNotFoundError:
    from config_example import TOKEN_SECRET_KEY

# Эта штука под капотом даже автоматически генерирует соль
token_generator = itsdangerous.URLSafeSerializer(TOKEN_SECRET_KEY)


def crypt(string: str) -> str:
    """
    Хэширует строку
    :param string: пароль или иная строка
    :return: хэш пароля
    """
    return pbkdf2_sha256.using(salt=bytes(TOKEN_SECRET_KEY, encoding="utf8"), rounds=1000).hash(string)


def verify(string: str, hashed: str) -> bool:
    """
    Сверяет хэш строки с данным хэшом
    :param string: строка, для которой проверяем хэш
    :param hashed: сверяемый хэш
    :return: True/False
    """
    return pbkdf2_sha256.using(salt=bytes(TOKEN_SECRET_KEY, encoding="utf8"), rounds=1000).verify(string, hashed)


