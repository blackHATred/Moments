import re
from html import escape

from tortoise import fields
from tortoise.backends.base.client import TransactionContext

from models.Abstracts import CreateTimestamp
from models.User import User


class Comment(CreateTimestamp):
    id = fields.IntField(pk=True)
    author = fields.ForeignKeyField("models.User", on_delete=fields.CASCADE)
    moment = fields.ForeignKeyField("models.Moment", on_delete=fields.CASCADE)
    text = fields.CharField(max_length=1024)

    class Meta:
        unique_together = ("moment", "author")

    @staticmethod
    async def parser(text: str, connection: TransactionContext | None = None) -> tuple[str, list[User]]:
        """
        Парсит содержание комментария и находит упоминания
        :param text: содержание комментария
        :param connection: подключение, которое следует использовать (указание на транзакцию извне этой функции)
        :return: HTML-raw готовый комментарий, список упоминаний
        """
        users: list[User] = []
        text = text.split()
        escaped_description = []
        # Проводим всё в транзакции
        for part in text:
            if part[0] == "@":
                # Упоминание другого пользователя
                string = re.sub(r'[^a-zA-Zа-яА-Я0-9]', '', part).lower()
                user = await User.get_or_none(nickname=string, using_db=connection)
                if user is not None:
                    users.append(user)
                    escaped_description.append(f'<a href="/user/{user.id}">{part}</a>')
                else:
                    escaped_description.append(escape(part, quote=True))
            else:
                escaped_description.append(escape(part, quote=True))

        return ' '.join(escaped_description), users

