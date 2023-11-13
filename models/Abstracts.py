from tortoise import fields
from tortoise.models import Model


class CreateTimestamp(Model):
    """
    Абстрактная модель для объектов, у которых следует хранить время создания
    """
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        abstract = True


class LikeableAbstract(CreateTimestamp):
    """
    Абстрактная модель объекта, который можно лайкнуть
    """
    id = fields.IntField(pk=True)
    author = fields.ForeignKeyField("models.User", on_delete=fields.CASCADE)

    class Meta:
        abstract = True


class LikeAbstract(CreateTimestamp):
    """
    Абстрактная модель лайка
    """
    id = fields.IntField(pk=True)
    author = fields.ForeignKeyField("models.User", on_delete=fields.CASCADE)

    class Meta:
        abstract = True
