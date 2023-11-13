import logging

from fastapi import APIRouter, UploadFile, HTTPException, BackgroundTasks
import tortoise.exceptions as exs
from starlette import status
from starlette.responses import RedirectResponse
from tortoise.transactions import in_transaction

from handlers.UploadHandler import upload_handler
from models.Moment import Moment
from models.MomentLike import MomentLike
from models.Notification import Notification
from models.User import UserDep, User

router = APIRouter()


@router.post("/create")
async def moment_create(user: UserDep, file: UploadFile, title: str, description: str,
                        background_tasks: BackgroundTasks):
    try:
        async with in_transaction() as connection:
            upload = await upload_handler.upload(file, connection)
            description, tags, recipients = await Moment.parser(description, connection)
            moment = await Moment.create(author=user, title=title, description=description, photo=upload, tags=tags,
                                         using_db=connection)
            for tag in tags:
                # Добавляем теги к посту
                await moment.tags.add(tag, using_db=connection)
            for recipient in recipients:
                # Отправляем уведомления пользователям, которых упомянули
                # TODO: сделать html текст уведомления
                await Notification.send_notification(
                    user=recipient,
                    html_text=f"Пользователь упомянул Вас",
                    background=background_tasks,
                    connection=connection
                )
        logging.info(f"Пользователь {user.id} выложил новый пост {moment.id}")
        return {"status": "success", "message": "Момент успешно создан"}
    except exs.IntegrityError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Не удалось создать момент с такими данными")
    except exs.ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Произошла ошибка валидации: {e}")
    except Exception as e:
        # Произошла ошибка иного рода - проблемы на сервере. Стоит залогировать
        logging.error(e, exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Произошла непредвиденная ошибка. Попробуйте повторить попытку чуть позже")


@router.get("/picture")
async def get_moment_picture(moment_id: int):
    try:
        moment = await Moment.get(id=moment_id).prefetch_related("picture")
        return RedirectResponse(upload_handler.download(moment.picture))
    except exs.DoesNotExist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)


@router.get("/info")
async def get_moment_info(moment_id: int):
    try:
        moment = await Moment.get(id=moment_id)
        return {
            "title": moment.title,
            "description": moment.description,
            "likes": await MomentLike.filter(object_id=moment).count(),
        }
    except exs.DoesNotExist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)


@router.put("/update")
async def update_moment(user: UserDep, moment_id: int, title: str, description: str):
    # Картинку обновлять нельзя! Это считается как новый момент
    try:
        async with in_transaction() as connection:
            moment = await Moment.get(id=moment_id, using_db=connection)
            if moment.author != user:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
            description, tags, users = await Moment.parser(description, connection)
            moment.tags.clear(using_db=connection)
            for tag in tags:
                moment.tags.add(tag, using_db=connection)
            moment.description = description
            moment.title = title
            await moment.save(using_db=connection)
        return {"status": "success"}
    except exs.DoesNotExist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    except exs.ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Произошла ошибка валидации: {e}")


@router.delete("/delete")
async def delete_moment(user: UserDep, moment_id: int):
    try:
        moment = await Moment.get(id=moment_id)
        if moment.author != user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
        # Подкапотно также удалятся все уведомления, отосланные при создании поста
        await moment.delete()
    except exs.DoesNotExist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)


@router.get("/user_moments")
async def user_moments(user_id: int, offset: int = 0):
    try:
        user = await User.get(id=user_id)
        return {
            "moments": await Moment.filter(author=user).offset(offset).limit(100).values_list("id", flat=True)
        }
    except exs.DoesNotExist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
