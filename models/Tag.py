from tortoise.models import Model
from tortoise import fields


class Tag(Model):
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=100, unique=True)
