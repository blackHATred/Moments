import re
from html import escape
from tortoise import fields
from tortoise.backends.base.client import TransactionContext

from models.Abstracts import CreateTimestamp
from models.User import User
from models.Tag import Tag


class Moment(CreateTimestamp):
    id = fields.IntField(pk=True)
    author = fields.ForeignKeyField("models.User", on_delete=fields.CASCADE)
    title = fields.CharField(max_length=128)
    description = fields.CharField(max_length=4096)
    views = fields.IntField(default=0)
    picture = fields.ForeignKeyField("models.Upload", on_delete=fields.CASCADE)
    tags = fields.ManyToManyField("models.Tag", related_name="moments", through='tagmoment')

    @staticmethod
    async def parser(description: str,
                     connection: TransactionContext | None = None) -> tuple[str, list[Tag], list[User]]:
        """
        Парсит описание момента и предлагает теги к посту. Также парсит все упоминания других пользователей
        :param description: Описание момента
        :param connection: подключение, которое следует использовать (указание на транзакцию извне этой функции)
        :return: HTML-raw готовое описание, список тегов, список упоминаний
        """
        users = []
        tags = []
        description = description.split()
        escaped_description = []
        # Проводим всё в транзакции
        for part in description:
            if part[0] == "@":
                # Упоминание другого пользователя
                string = re.sub(r'[^a-zA-Zа-яА-Я0-9_]', '', part).lower()
                user = await User.get_or_none(nickname=string, using_db=connection)
                if user is not None:
                    users.append(user)
                    escaped_description.append(f'<a href="/user/{user.id}">{part}</a>')
                else:
                    escaped_description.append(escape(part, quote=True))
            elif part[0] == "#" and 1 < len(part) < 102:
                # Тэг
                string = re.sub(r'[^a-zA-Zа-яА-Я0-9]', '', part).lower()
                tag = (await Tag.get_or_create(name=string, using_db=connection))[0]
                tags.append(tag)
                escaped_description.append(part)
            else:
                escaped_description.append(escape(part, quote=True))

        return ' '.join(escaped_description), tags, users




