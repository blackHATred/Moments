from tortoise import fields

from models.Abstracts import LikeAbstract


class MomentLike(LikeAbstract):
    object = fields.ForeignKeyField("models.Moment", on_delete=fields.CASCADE)

    class Meta:
        unique_together = ("object", "author")

