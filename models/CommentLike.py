from tortoise import fields

from models.Abstracts import CreateTimestamp


class CommentLike(CreateTimestamp):
    id = fields.IntField(pk=True)
    author = fields.ForeignKeyField("models.User", on_delete=fields.CASCADE)
    object = fields.ForeignKeyField("models.Comment", on_delete=fields.CASCADE)

    class Meta:
        unique_together = ("object", "author")

