import logging

from fastapi import APIRouter, HTTPException, BackgroundTasks
import tortoise.exceptions as exs
from starlette import status
from tortoise.transactions import in_transaction

from models.Comment import Comment
from models.CommentLike import CommentLike
from models.Moment import Moment
from models.Notification import Notification
from models.User import UserDep

router = APIRouter()


@router.post("/create")
async def create_comment(user: UserDep, moment_id: int, text: str, background_tasks: BackgroundTasks):
    """
    Создание комментария под моментом. Допустимо создание не более одного комментария пользователя под одним моментом
    :param user: пользователь, от лица которого совершается действие
    :param moment_id: айди момента
    :param text: содержание комментария
    :return: {"status": "success", "message": "Комментарий успешно отправлен"} при успехе, иначе - ошибка 4xx
    """
    try:
        async with in_transaction() as connection:
            moment = await Moment.get(id=moment_id, using_db=connection)
            # Проверяем, возможно комментарий уже существует. Запрещено отправлять более одного комментария
            if await Comment.exists(author=user, moment=moment, using_db=connection):
                raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                                    detail="Комментарий под этим моментом уже стоит")
            text, recipients = await Comment.parser(text, connection)
            comment = await Comment.create(author=user, moment=moment, text=text, using_db=connection)
            for recipient in recipients:
                # Отправляем уведомления пользователям, которых упомянули
                # TODO: сделать html текст уведомления
                await Notification.send_notification(
                    user=recipient,
                    html_text=f"Пользователь упомянул Вас",
                    background=background_tasks,
                    connection=connection,
                    pinned_user=user,
                    pinned_post=moment,
                    pinned_comment=comment
                )
            logging.info(f"Пользователь {user.id} оставил комментарий на пост {moment.id}")
        return {"status": "success", "message": "Комментарий успешно отправлен"}
    except exs.DoesNotExist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Такой момент не существует")
    except Exception as e:
        # Произошла ошибка иного рода - проблемы на сервере. Стоит залогировать
        logging.error(e, exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Произошла непредвиденная ошибка. Попробуйте повторить попытку чуть позже")


@router.put("/update")
async def update_comment(user: UserDep, comment_id: int, text: str, background_tasks: BackgroundTasks):
    """
    Обновление содержания комментария
    :param user: пользователь, от лица которого совершается действие
    :param comment_id: айди комментария
    :param text: новое содержание комментария
    :return: {"status": "success", "message": "Комментарий успешно обновлён"} при успехе, иначе - ошибка 4xx
    """
    try:
        async with in_transaction() as connection:
            comment = await Comment.get(id=comment_id, using_db=connection).prefetch_related("author")
            if comment.author != user:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
            text, recipients = await Comment.parser(text, connection)
            for recipient in recipients:
                # Отправляем уведомления пользователям, которых упомянули
                # TODO: сделать html текст уведомления
                await Notification.send_notification(
                    user=recipient,
                    html_text=f'Пользователь <a href="/user/{user.id}">@{user.nickname}</a>упомянул Вас',
                    background=background_tasks,
                    connection=connection,

                )
            comment.text = text
            comment.save(using_db=connection)
        return {"status": "success", "message": "Комментарий успешно обновлён"}
    except exs.DoesNotExist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Такой комментарий не существует")
    except Exception as e:
        # Произошла ошибка иного рода - проблемы на сервере. Стоит залогировать
        logging.error(e, exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Произошла непредвиденная ошибка. Попробуйте повторить попытку чуть позже")


@router.get("/moment_comments")
async def get_moment_comments(moment_id: int, offset: int = 0):
    """
    Возвращает комментарии под моментом
    :param moment_id: айди момента, под которым хотим получить комментарии
    :param offset: офсет списка комментариев
    :return: комментарии в виде {"comments": [...]}
    """
    try:
        moment = await Moment.get(id=moment_id)
        comments = await Comment.filter(moment=moment).offset(offset).limit(100).values_list("id", flat=True)
        return {
            "comments": comments
        }
    except exs.DoesNotExist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)


@router.get("/moment_comment")
async def get_moment_comment(comment_id: int):
    """
    Возвращает информацию о комментарии под моментом
    :param comment_id: айди комментария
    :return: информация в виде {"author": айди_автора, "text": "содержание комментария", "likes": количество_лайков}
    """
    try:
        comment = await Comment.get(id=comment_id).prefetch_related("author")
        return {
            "author": comment.author.id,
            "text": comment.text,
            "likes": await CommentLike.filter(comment=comment)
        }
    except exs.DoesNotExist():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
