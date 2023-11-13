from tortoise import fields

from models.Abstracts import CreateTimestamp


class Subscription(CreateTimestamp):
    id = fields.IntField(pk=True)
    author = fields.ForeignKeyField("models.User", on_delete=fields.CASCADE, related_name="author_subscriptions")
    subscriber = fields.ForeignKeyField("models.User", on_delete=fields.CASCADE, related_name="subscriptions")
