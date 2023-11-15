from tortoise import fields

from models.Abstracts import CreateTimestamp


class MomentLike(CreateTimestamp):
    id = fields.IntField(pk=True)
    author = fields.ForeignKeyField("models.User", on_delete=fields.CASCADE)
    object = fields.ForeignKeyField("models.Moment", on_delete=fields.CASCADE)

    class Meta:
        unique_together = ("object", "author")

