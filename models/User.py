import base64
import re
from typing import Annotated

from fastapi import Depends, HTTPException
from itsdangerous import BadSignature
from starlette import status
from tortoise import fields
from tortoise.exceptions import DoesNotExist, ValidationError
from tortoise.validators import MinLengthValidator

from handlers.CacheHandler import mc
from misc.secure import crypt, token_generator
from models.Abstracts import CreateTimestamp
from models.validators import EmailValidator


class User(CreateTimestamp):
    id = fields.IntField(pk=True)
    email = fields.CharField(max_length=2048, unique=True, validators=[EmailValidator()])
    nickname = fields.CharField(max_length=100, unique=True, validators=[MinLengthValidator(3)])
    password = fields.CharField(max_length=1024)
    avatar = fields.OneToOneField("models.Upload", on_delete=fields.SET_NULL, null=True, default=None)
    uploads = fields.ManyToManyField("models.Upload", on_delete=fields.SET_NULL)
    rating = fields.IntField(default=0)

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
            return encrypted.decode("utf-8")

    def get_token(self) -> str:
        """
        Получить токен сессии
        :return: токен
        """
        # Пароль тоже включаем в нагрузку. Тогда если юзер сменит пароль на одном девайсе, то со всех остальных
        # он выйдет автоматически, т.к. старые токены перестанут работать.
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
        try:
            payload = token_generator.loads(token)
            user = await User.get(id=payload.get('id'))
            if user.password != payload.get('password'):
                # Неверный пароль равносилен несуществующему пользователю
                raise DoesNotExist
        except (DoesNotExist, BadSignature):
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
    async def validate_password(password: str):
        password_pattern = re.compile(r'^(?=.*\d)(?=.*[!@#$%^&*(),.?\":{}|<>])[A-Za-z\d!@#$%^&*(),.?\":{}|<>]{8,128}$')
        if not re.match(password_pattern, password):
            raise ValidationError("Пароль должен содержать как минимум одну цифру и один специальный символ и "
                                  "иметь длину от 8 до 128 символов")


UserDep = Annotated[User, Depends(User.get_from_token)]

