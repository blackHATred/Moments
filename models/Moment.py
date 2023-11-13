from html import escape
from tortoise import fields, Model
from tortoise.backends.base.client import TransactionContext
from tortoise.transactions import in_transaction

from models.User import User
from models.Abstracts import LikeableAbstract
from models.Tag import Tag


class Moment(LikeableAbstract, Model):
    title = fields.CharField(max_length=128)
    description = fields.CharField(max_length=4096)
    picture = fields.ForeignKeyField("models.Upload", on_delete=fields.CASCADE)
    tags = fields.ManyToManyField("models.Tag", related_name="moments", through='tagmoment')

    @staticmethod
    async def parser(description: str, connection: TransactionContext | None = None) -> tuple[str, list[Tag], list[User]]:
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
                user = await User.get_or_none(nickname=part[1:], using_db=connection)
                if user is not None:
                    users.append(user)
                    escaped_description.append(f'<a href="/user/{user.id}">{part}</a>')
                else:
                    escaped_description.append(escape(part, quote=True))
            elif part[0] == "#" and 1 < len(part) < 102:
                # Тэг
                tag = (await Tag.get_or_create(name=part[1:].lower(), using_db=connection))[0]
                tags.append(tag)
                escaped_description.append(part)
            else:
                escaped_description.append(escape(part, quote=True))

        return ''.join(escaped_description), tags, users


class TagMoment(Model):
    moment = fields.ForeignKeyField('models.Moment', on_delete=fields.RESTRICT)
    tag = fields.ForeignKeyField('models.Tag', on_delete=fields.RESTRICT)

