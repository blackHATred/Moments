import logging

from fastapi import APIRouter, HTTPException
import tortoise.exceptions as exs
from starlette import status

from models.Subscription import Subscription
from models.User import User, UserDep

router = APIRouter()


@router.post("/subscribe")
async def subscribe(user: UserDep, author_id: int):
    try:
        author = await User.get(id=author_id)
        # Проверяем, возможно пользователь уже подписан
        if not await Subscription.exists(author=author, subscriber=user):
            await Subscription.create(author=author, subscriber=user)
        logging.info(f"Пользователь {user.id} подписался на {author.id}")
        return {"status": "success", "message": "Подписка успешно оформлена"}
    except exs.DoesNotExist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Такой автор не существует")
    except Exception as e:
        # Произошла ошибка иного рода - проблемы на сервере. Стоит залогировать
        logging.error(e, exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Произошла непредвиденная ошибка. Попробуйте повторить попытку чуть позже")


@router.post("/unsubscribe")
async def unsubscribe(user: UserDep, author_id: int):
    try:
        author = await User.get(id=author_id)
        # Проверяем, подписан ли пользователь
        if await Subscription.exists(author=author, subscriber=user):
            await (await Subscription.get(author=author, subscriber=user)).delete()
        logging.info(f"Пользователь {user.id} отписался от {author.id}")
        return {"status": "success", "message": "Подписка успешно оформлена"}
    except exs.DoesNotExist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Такой автор не существует")
    except Exception as e:
        # Произошла ошибка иного рода - проблемы на сервере. Стоит залогировать
        logging.error(e, exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Произошла непредвиденная ошибка. Попробуйте повторить попытку чуть позже")