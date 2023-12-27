import logging

from cent import CentException
from fastapi import BackgroundTasks
from tortoise import fields
from tortoise.backends.base.client import TransactionContext


from handlers.CentrifugoHandler import cent_client
from models.Abstracts import CreateTimestamp
from models.User import User


class Notification(CreateTimestamp):
    id = fields.IntField(pk=True)
    text = fields.CharField(max_length=1024)
    read = fields.BooleanField(default=False)
    recipient = fields.ForeignKeyField("models.User", on_delete=fields.CASCADE)

    @staticmethod
    async def send_notification(user: User, html_text: str, background: BackgroundTasks,
                                connection: TransactionContext | None = None):
        """
        Отправка уведомления пользователю
        :param user: Пользователь, которому надо отправить уведомление.
        :param html_text: Html-содержимое уведомления
        :param background: фоновый контекст FastAPI
        :param connection: Подключение, которое следует использовать (указание на транзакцию извне этой функции)
        :return: Notification
        """
        notification = await Notification.create(text=html_text, recipient=user, using_db=connection)
        background.add_task(Notification.cent_send_notification, user, notification.text)

    @staticmethod
    async def cent_send_notification(user: User, text: str):
        """
        Отправляет подписчику на уведомления текст уведомления в centrifugo
        :param user: пользователь, которому нужно отправить уведомление
        :param text: содержание уведомления
        """
        try:
            cent_client.publish(f"personal_notifications:{user.id}", {"data": text})
        except CentException as e:
            # Ошибка некритична, но её стоит отследить
            logging.error(e, exc_info=True)

    @staticmethod
    async def get_unread_notifications(user: User):
        # Будем отправлять не более 10 уведомлений за раз. Кроме содержимого уведомлений больше ничего не нужно
        return await (Notification
                      .filter(recipient=user, read=False)
                      .order_by("-created_at")
                      .limit(10)
                      .values_list("text"))

    @staticmethod
    async def set_read_all(user: User):
        # Помечаем все уведомления прочитанными
        await (Notification
               .filter(recipient=user, read=False)
               .update(read=True))
        # Очищаем историю
        cent_client.history_remove(f"personal_notifications:{user.id}")


