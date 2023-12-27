import logging

from fastapi import APIRouter, HTTPException, BackgroundTasks
import tortoise.exceptions as exs
from starlette import status
from tortoise.expressions import Q
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
    :param background_tasks: менеджер фоновых задач FastAPI
    :return: {"status": "success"} при успехе, иначе - ошибка 4xx
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
                await Notification.send_notification(
                    user=recipient,
                    html_text=f"Пользователь <a href=\"/user/{user.id}\">@{user.nickname}</a> упомянул вас в своём "
                              f"комментарии под <a href=\"/moment/{moment.id}\">моментом</a>",
                    background=background_tasks,
                    connection=connection
                )
            logging.info(f"Пользователь {user.id} оставил комментарий на пост {moment.id}")
        return {"status": "success"}
    except exs.DoesNotExist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Такой момент не существует")


@router.delete("/delete")
async def delete_comment(user: UserDep, comment_id: int):
    """
    Удаляет выбранный комментарий пользователя
    :param user: пользователь, от лица которого совершается действие
    :param comment_id: айди комментария
    :return: {"status": "success", "message": "Комментарий успешно удалён"} при успехе, иначе - ошибка 4хх
    """
    try:
        comment = await Comment.get(id=comment_id).prefetch_related("author")
        if comment.author != user:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
        await comment.delete()
        return {"status": "success", "message": "Комментарий успешно удалён"}
    except exs.DoesNotExist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Такой комментарий не существует")


@router.get("/get_comments")
async def get_moment_comments(user: UserDep, moment_id: int, last_comment: int = 0):
    """
    Возвращает комментарии под моментом
    :param user: пользователь
    :param moment_id: айди момента, под которым хотим получить комментарии
    :param last_comment: айди последнего полученного комментария
    :return: комментарии в виде {"comments": [...]}
    """
    try:
        moment = await Moment.get(id=moment_id)
        comments = Comment.filter(moment=moment)
        return {
            "total": await comments.count(),
            "comments": await (comments
                               .order_by("-created_at")
                               .exclude(Q(id__lt=last_comment))
                               .exclude(author=user)
                               .limit(10)
                               .values_list("id", flat=True))
        }
    except exs.DoesNotExist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)


@router.get("/get_comment")
async def get_moment_comment(user: UserDep, comment_id: int):
    """
    Возвращает информацию о комментарии под моментом
    :param user: пользователь
    :param comment_id: айди комментария
    :return: информация в виде {"author": айди_автора, "text": "содержание комментария", "likes": количество_лайков}
    """
    try:
        comment = await Comment.get(id=comment_id).prefetch_related("author")
        return {
            "author": comment.author.id,
            "author_nickname": comment.author.nickname,
            "text": comment.text,
            "likes": await CommentLike.filter(object=comment).count(),
            "liked": await CommentLike.filter(author=user, object=comment).exists()
        }
    except exs.DoesNotExist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)


@router.get("/my_comment")
async def get_my_comment(user: UserDep, moment_id: int):
    """
    Получить свой комментарий под указанным моментом
    :param user: пользователь, от лица которого совершается действие
    :param moment_id: айди момент
    :return: {"comment": comment.id} либо {"comment": null}
    """
    try:
        moment = await Moment.get(id=moment_id)
        comment = await Comment.get_or_none(moment=moment, author=user)
        return {"comment": comment.id if comment is not None else None}
    except exs.DoesNotExist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
