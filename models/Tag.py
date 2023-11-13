from tortoise.models import Model
from tortoise import fields

from models.Moment import Moment


class Tag(Model):
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=100, unique=True)
    moments: fields.ManyToManyRelation[Moment]
