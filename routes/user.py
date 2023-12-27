import logging

from fastapi import APIRouter, UploadFile, HTTPException
import tortoise.exceptions as exs
from starlette import status
from starlette.responses import RedirectResponse
from tortoise.transactions import in_transaction

from handlers.CentrifugoHandler import get_cent_token
from handlers.UploadHandler import upload_handler
from models.Subscription import Subscription
from models.User import User, UserDep

router = APIRouter()


@router.post("/register")
async def user_register(email: str, nickname: str, password: str):
    try:
        await User.validate_password(password)
        user = await User.create(email=email.lower(), nickname=nickname.lower(), password=User.crypt_password(password))
        logging.info(f"Зарегистрирован пользователь {user.id}")
        return {"status": "success"}
    except exs.IntegrityError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=r"Пользователь с такой почтой и\или никнеймом уже существует")
    except exs.ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Произошла ошибка валидации: {e}")


@router.post("/login")
async def user_login(login: str, password: str):
    try:
        user = await User.get_or_none(nickname=login.lower().strip(), password=User.crypt_password(password))
        if user is None:
            # Если не нашли по никнейму, то пробуем найти по почте
            user = await User.get(email=login.lower().strip(), password=User.crypt_password(password))
        return {"status": "success", "token": user.get_token()}
    except (exs.DoesNotExist, exs.ValidationError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)


@router.put("/update_info")
async def user_update_info(user: UserDep, email: str | None, nickname: str | None):
    if email is not None:
        user.email = email.lower().strip()
    if nickname is not None:
        user.nickname = nickname.lower().strip()
    try:
        await user.save()
    except exs.IntegrityError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=r"Пользователь с такой почтой и\или никнеймом уже существует")
    except exs.ValidationError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Проверьте корректность введённых данных")
    else:
        return {"new_email": user.email, "new_nickname": user.nickname}


@router.put("/update_avatar")
async def user_update_avatar(user: UserDep, file: UploadFile):
    try:
        async with in_transaction() as connection:
            upload = await upload_handler.upload(file, connection)
            user.avatar = upload
            await user.save(using_db=connection)
        return {"status": "success"}
    except exs.IntegrityError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Произошла неожиданная ошибка")


@router.put("/update_password")
async def user_update_password(user: UserDep, current_password: str, new_password: str):
    if user.password != User.crypt_password(current_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Неверный пароль")
    try:
        await User.validate_password(new_password)
        # Если обновляем пароль, то чистим кэш
        await user.clear_cache()
        user.password = User.crypt_password(new_password)
        # !!! Пользователь вылетит, так как его токен станет невалидным!
        await user.save()
        return {"status": "success"}
    except (exs.IntegrityError, exs.ValidationError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Новый пароль некорректен")


@router.get("/avatar")
async def get_avatar(user_id: int):
    try:
        user = await User.get(id=user_id).prefetch_related("avatar")
        if user.avatar is None:
            # Если аватарки нет, то отображаем стандартную
            return RedirectResponse(upload_handler.download_default_avatar())
        return RedirectResponse(upload_handler.download(user.avatar))
    except exs.DoesNotExist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)


@router.get("/my_info")
async def get_my_info(user: UserDep):
    return {
        "id": user.id,
        "email": user.email,
        "nickname": user.nickname,
        "rating": user.rating,
        "reg_date": user.created_at,
        "followers": await Subscription.filter(author=user).count(),
        "subscriptions": await Subscription.filter(subscriber=user).count()
    }


@router.get("/user_info")
async def get_info(client: UserDep, user_id: int):
    try:
        user = await User.get(id=user_id)
        return {
            "id": user.id,
            "email": user.email,
            "nickname": user.nickname,
            "rating": user.rating,
            "reg_date": user.created_at,
            "followers": await Subscription.filter(author=user).count(),
            "subscriptions": await Subscription.filter(subscriber=user).count(),
            "subscribed": await Subscription.filter(author=user, subscriber=client).exists()
        }
    except exs.DoesNotExist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)


# TODO: Добавить возможность авторизации через SSO
