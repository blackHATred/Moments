from tortoise import fields

from models.Abstracts import LikeAbstract


class CommentLike(LikeAbstract):
    object = fields.ForeignKeyField("models.Comment", on_delete=fields.CASCADE)

    class Meta:
        unique_together = ("object", "author")

