from fastapi import APIRouter, HTTPException
from starlette import status

from models.Notification import Notification
from models.User import UserDep
import tortoise.exceptions as exs

router = APIRouter()


@router.get("/get")
async def get_notification(user: UserDep, notification_id: int):
    try:
        print(await Notification.all().values())
        notification = await Notification.get(id=notification_id, recipient=user)
        return {"notification": notification.text}
    except exs.DoesNotExist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
