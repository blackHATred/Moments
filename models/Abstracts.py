from tortoise import fields
from tortoise.models import Model


class CreateTimestamp(Model):
    """
    Абстрактная модель для объектов, у которых следует хранить время создания
    """
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        abstract = True
