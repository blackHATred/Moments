import logging

from fastapi import APIRouter, HTTPException
import tortoise.exceptions as exs
from starlette import status

from models.Comment import Comment
from models.CommentLike import CommentLike
from models.Moment import Moment
from models.MomentLike import MomentLike
from models.User import UserDep

router = APIRouter()


@router.post("/like_moment")
async def like_moment(user: UserDep, moment_id: int):
    try:
        moment = await Moment.get(id=moment_id)
        # Проверяем, возможно лайк уже поставлен
        if not await MomentLike.exists(author=user, object=moment):
            await MomentLike.create(author=user, object=moment)
        logging.info(f"Пользователь {user.id} поставил лайк на момент {moment.id}")
        return {"status": "success", "message": "Лайк на момент успешно поставлен"}
    except exs.DoesNotExist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Такого момента не существует")


@router.post("/unlike_moment")
async def unlike_moment(user: UserDep, moment_id: int):
    try:
        moment = await Moment.get(id=moment_id)
        # Проверяем, возможно лайк и так не стоит
        if await MomentLike.exists(author=user, object=moment):
            await (await MomentLike.get(author=user, object=moment)).delete()
        logging.info(f"Пользователь {user.id} убрал лайк с момента {moment.id}")
        return {"status": "success", "message": "Лайк успешно убран"}
    except exs.DoesNotExist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Такого момента не существует")


@router.get("/is_moment_liked")
async def is_moment_liked(user: UserDep, moment_id: int):
    try:
        moment = await Moment.get(id=moment_id)
        return {"liked": await MomentLike.exists(author=user, object=moment)}
    except exs.DoesNotExist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Такого момента не существует")


@router.post("/like_comment")
async def like_comment(user: UserDep, comment_id: int):
    try:
        comment = await Comment.get(id=comment_id)
        # Проверяем, возможно лайк на комментарий уже поставлен
        if not await CommentLike.exists(author=user, object=comment):
            await CommentLike.create(author=user, object=comment)
        logging.info(f"Пользователь {user.id} поставил лайк на комментарий {comment.id}")
        return {"status": "success", "message": "Лайк на комментарий успешно поставлен"}
    except exs.DoesNotExist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Такого комментария не существует")


@router.post("/unlike_comment")
async def unlike_comment(user: UserDep, comment_id: int):
    try:
        comment = await Comment.get(id=comment_id)
        # Проверяем, возможно лайк и так не стоит
        if await CommentLike.exists(author=user, object=comment):
            await (await CommentLike.get(author=user, object=comment)).delete()
        logging.info(f"Пользователь {user.id} убрал лайк с комментария {comment.id}")
        return {"status": "success", "message": "Лайк успешно убран"}
    except exs.DoesNotExist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Такого комментария не существует")


@router.get("/is_comment_liked")
async def is_comment_liked(user: UserDep, comment_id: int):
    try:
        comment = await Comment.get(id=comment_id)
        return {"liked": await MomentLike.exists(author=user, object=comment)}
    except exs.DoesNotExist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Такого комментария не существует")
