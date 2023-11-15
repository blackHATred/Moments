from tortoise import Model, fields


class TagMoment(Model):
    moment = fields.ForeignKeyField('models.Moment', on_delete=fields.RESTRICT)
    tag = fields.ForeignKeyField('models.Tag', on_delete=fields.RESTRICT)
