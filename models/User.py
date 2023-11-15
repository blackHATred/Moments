import re
from typing import Annotated

from fastapi import Depends, HTTPException
from starlette import status
from tortoise import fields
from tortoise.exceptions import DoesNotExist, ValidationError

from handlers.CacheHandler import mc
from misc.secure import crypt, token_generator
from models.Abstracts import CreateTimestamp


class User(CreateTimestamp):
    id = fields.IntField(pk=True)
    email = fields.CharField(max_length=2048, unique=True)
    nickname = fields.CharField(max_length=100, unique=True)
    password = fields.CharField(max_length=1024)
    avatar = fields.OneToOneField("models.Upload", on_delete=fields.SET_NULL, null=True, default=None)
    uploads = fields.ManyToManyField("models.Upload", on_delete=fields.SET_NULL)
    rating = fields.IntField(default=0)

    async def save(self, *args, **kwargs):
        if not self.is_valid_email(self.email):
            raise ValidationError("Неверный email адрес")
        User.validate_password(self.password)

        await super().save(*args, **kwargs)

    @staticmethod
    def crypt_password(password: str) -> str:
        # Используем кэш
        encrypted = mc.get(f"crypt_password:{password}")
        if encrypted is None:
            # Cache miss
            encrypted = crypt(password)
            mc.set(f"crypt_password:{password}", encrypted)
            return encrypted
        else:
            return encrypted.decode('utf-8')

    def get_token(self) -> str:
        """
        Получить токен сессии
        :return: токен
        """
        # Пароль тоже включаем в нагрузку. Тогда если юзер сменит пароль на одном девайсе, то со всех остальных
        # он выйдет автоматически, т.к. старые токены перестанут работать. Вот такая фича.
        # Используем кэш
        token = mc.get(f"user_token:{self.id}")
        if token is None:
            # Cache miss
            token = token_generator.dumps({'id': self.id, 'password': self.password})
            mc.set(f"user_token:{self.id}", token)
            return token
        else:
            return token.decode('utf-8')

    @staticmethod
    async def get_from_token(token: str):
        """
        Возвращает пользователя из токена
        :param token: токен
        :return: User
        """
        payload = token_generator.loads(token)
        try:
            user = await User.get(id=payload.get('id'))
            if user.password != payload.get('password'):
                # Неверный пароль равносилен несуществующему пользователю
                raise DoesNotExist
        except DoesNotExist:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        else:
            return user

    async def clear_cache(self) -> None:
        """
        Удаляет токен пользователя из кэша
        :return: None
        """
        mc.delete(f"user_token:{self.id}")

    @staticmethod
    def is_valid_email(email):
        # Регулярное выражение для валидации email-адреса
        email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
        return bool(re.match(email_pattern, email))

    @staticmethod
    def validate_password(password):
        if len(password) < 8:
            raise ValidationError("Пароль должен содержать минимум 8 символов")
        if not re.search("[0-9]", password):
            raise ValidationError("Пароль должен содержать минимум одну цифру")
        if not re.search("[!@#$%^&*(),.?\":{}|<>]", password):
            raise ValidationError("Пароль должен содержать минимум один специальный символ")


UserDep = Annotated[User, Depends(User.get_from_token)]

