from tortoise import fields

from models.Abstracts import CreateTimestamp


class Upload(CreateTimestamp):
    id = fields.IntField(pk=True)
    filename = fields.CharField(max_length=1000)
