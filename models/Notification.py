import logging

from cent import CentException
from fastapi import BackgroundTasks
from tortoise import fields
from tortoise.backends.base.client import TransactionContext

from handlers.CentrifugoHandler import cent_client
from models.Abstracts import CreateTimestamp
from models.Comment import Comment
from models.Moment import Moment
from models.User import User


class Notification(CreateTimestamp):
    id = fields.IntField(pk=True)
    text = fields.CharField(max_length=1024)
    recipient = fields.ForeignKeyField("models.User", on_delete=fields.CASCADE)
    pinned_post = fields.ForeignKeyField("models.Moment", on_delete=fields.CASCADE, null=True, default=None)
    pinned_comment = fields.ForeignKeyField("models.Comment", on_delete=fields.CASCADE, null=True,
                                            default=None)
    pinned_user = fields.ForeignKeyField("models.User", on_delete=fields.CASCADE, null=True, default=None)

    @staticmethod
    async def send_notification(user: User, html_text: str, background: BackgroundTasks,
                                pinned_post: Moment | None = None, pinned_comment: Comment | None = None,
                                pinned_user: User | None = None, connection: TransactionContext | None = None):
        """
        Отправка уведомления пользователю
        :param user: Пользователь, которому надо отправить уведомление.
        :param html_text: Html-содержимое уведомления
        :param background: фоновый контекст FastAPI
        :param pinned_post: Связанный с уведомлением момент
        :param pinned_comment: Связанный с уведомлением комментарий
        :param pinned_user: Связанный с уведомлением пользователь
        :param connection: Подключение, которое следует использовать (указание на транзакцию извне этой функции)
        :return: Notification
        """
        notification = await Notification.create(text=html_text, user=user, pinned_post=pinned_post,
                                                 pinned_comment=pinned_comment,  pinned_user=pinned_user,
                                                 using_db=connection)
        background.add_task(Notification.cent_send_notification, user, notification.text)

    @staticmethod
    async def cent_send_notification(user: User, text: str):
        """
        Отправляет подписчику на уведомления текст уведомления в centrifugo
        :param user: пользователь, которому нужно отправить уведомление
        :param text: содержание уведомления
        """
        try:
            cent_client.publish(f"notifications:{user.id}", text)
        except CentException as e:
            # Ошибка некритична, но её стоит отследить
            logging.error(e, exc_info=True)

