from fastapi import APIRouter
from starlette.requests import Request
from tortoise.expressions import Q

from models.Notification import Notification
from models.User import UserDep, User

router = APIRouter()


@router.post("/connect")
async def connect(request: Request):
    """
    Специальный хэндлер для centrifugo, не предназначен для вызова с фронта. Выдаёт права пользователю
    и отправляет все непрочитанные уведомления
    """
    # Пользователь подключается к centrifugo, нужно отдать центрифуге айди юзера и все непрочитанные уведомления
    user_token = (await request.json()).get("data").get("token")
    user = await User.get_from_token(user_token)
    notifications = await Notification.get_unread_notifications(user)
    return {"result": {"user": str(user.id), "channels": [f"personal_notifications:{user.id}"], "data": notifications}}


@router.post("/set_read")
async def set_read(user: UserDep):
    """
    Пометить все уведомления прочитанными
    :param user: токен пользователя
    """
    await Notification.set_read_all(user)
    return {"success": True}


@router.get("/read")
async def read(user: UserDep, last_read: int = 0):
    """
    Получить 10 уведомлений, начиная с last_read
    :param last_read: айди последнего прочитанного уведомления (0 == получить все уведомления, начиная с первого)
    :param user: токен пользователя
    """
    return await (Notification
                  .filter(recipient=user)
                  .order_by("-created_at")
                  .exclude(Q(id__lt=last_read))
                  .limit(10)
                  .values_list("id", "text"))
