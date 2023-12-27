import logging

from fastapi import APIRouter, UploadFile, HTTPException, BackgroundTasks
import tortoise.exceptions as exs
from starlette import status
from starlette.responses import RedirectResponse
from tortoise.expressions import Q
from tortoise.transactions import in_transaction

from handlers.UploadHandler import upload_handler
from models.Moment import Moment
from models.MomentLike import MomentLike
from models.Notification import Notification
from models.Subscription import Subscription
from models.TagMoment import TagMoment
from models.User import UserDep, User

router = APIRouter()


@router.post("/create")
async def moment_create(user: UserDep, file: UploadFile, title: str, description: str,
                        background_tasks: BackgroundTasks):
    try:
        async with in_transaction() as connection:
            upload = await upload_handler.upload(file, connection)
            description, tags, recipients = await Moment.parser(description, connection)
            moment = await Moment.create(author=user, title=title, description=description, picture=upload,
                                         using_db=connection)
            for tag in tags:
                # Добавляем теги к посту
                await moment.tags.add(tag, using_db=connection)
            for recipient in recipients:
                # Отправляем уведомления пользователям, которых упомянули
                await Notification.send_notification(
                    user=recipient,
                    html_text=f"Пользователь <a href=\"/user/{user.id}\">@{user.nickname}</a> упомянул вас в своём "
                              f"<a href=\"/moment/{moment.id}\">моменте</a>",
                    background=background_tasks,
                    connection=connection
                )
        logging.info(f"Пользователь {user.id} выложил новый пост {moment.id}")
        return {"status": "success"}
    except exs.IntegrityError as e:
        logging.error(e, exc_info=True)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Не удалось создать момент с такими данными")
    except exs.ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Произошла ошибка валидации: {e}")


@router.get("/picture")
async def get_moment_picture(moment_id: int):
    try:
        moment = await Moment.get(id=moment_id).prefetch_related("picture")
        return RedirectResponse(upload_handler.download(moment.picture))
    except exs.DoesNotExist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)


@router.get("/get")
async def get_moment_info(user: UserDep, moment_id: int):
    try:
        moment = await Moment.get(id=moment_id).prefetch_related("tags", "author")
        # Каждый такой запрос от фронтенда будем считать как один просмотр. При этом пользователь может посмотреть
        # момент несколько раз - на это ограничений нет (похожим образом сделано, к примеру, в ютубе, хотя,
        # конечно же, было бы неплохо добавить защиту от накрутки просмотров)
        moment.views += 1
        await moment.save()
        return {
            "title": moment.title,
            "description": moment.description,
            "likes": await MomentLike.filter(object=moment).count(),
            "views": moment.views,
            "tags": [tag.name for tag in moment.tags],
            "author": moment.author.id,
            "liked": await MomentLike.filter(author=user, object=moment).exists()
        }
    except exs.DoesNotExist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)


@router.get("/user_moments")
async def user_moments(user_id: int, last_moment: int = 0):
    try:
        user = await User.get(id=user_id)
        return {
            "moments": await Moment
            .filter(author=user)
            .order_by("-created_at")
            .exclude(Q(id__lt=last_moment))
            .limit(10)
            .values_list("id", flat=True)
        }
    except exs.DoesNotExist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)


@router.get("/feed")
async def feed(user: UserDep, last_moment: int = 0):
    subscriptions = await Subscription.filter(subscriber=user).values_list("author_id", flat=True)
    return {
        "moments": await Moment
        .filter(Q(author_id__in=subscriptions))
        .exclude(Q(id__lt=last_moment))
        .order_by("-created_at")
        .limit(10)
        .values_list("id", flat=True)
    }


@router.get("/search")
async def search(phrase: str, last_moment: int = 0):
    possible_user = await User.get_or_none(nickname=phrase)
    return {
        "moments": await TagMoment
        .filter(Q(tag__name=phrase))
        .exclude(Q(id__lt=last_moment))
        .limit(10)
        .values_list("moment_id", flat=True),
        "user": possible_user.id if possible_user is not None else None
    }
