import logging

from fastapi import APIRouter, UploadFile, HTTPException
import tortoise.exceptions as exs
from starlette import status
from starlette.responses import RedirectResponse

from handlers.CentrifugoHandler import get_cent_token
from handlers.UploadHandler import upload_handler
from models.User import User, UserDep

router = APIRouter()


@router.post("/register")
async def user_register(email: str, nickname: str, password: str):
    try:
        user = await User.create(email=email, nickname=nickname, password=User.crypt_password(password))
        logging.info(f"Зарегистрирован пользователь {user.id}")
        return {"status": "success", "message": "Пользователь успешно создан"}
    except exs.IntegrityError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=r"Пользователь с таким логином и\или никнеймом уже существует")
    except exs.ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Произошла ошибка валидации: {e}")


@router.post("/login")
async def user_login(login: str, password: str):
    try:
        user = await User.get_or_none(nickname=login, password=User.crypt_password(password))
        if user is None:
            # Если не нашли по никнейму, то пробуем найти по почте
            user = await User.get(email=login, password=User.crypt_password(password))
        return {"status": "success", "token": user.get_token()}
    except exs.DoesNotExist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)


@router.put("/update_info")
async def user_update_info(user: UserDep, email: str | None, nickname: str | None):
    if email is not None:
        user.email = email
    if nickname is not None:
        user.nickname = nickname
    try:
        await user.save()
    except exs.ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=fr"Произошла ошибка валидации: {e}")
    else:
        return {"status": "success", "message": "Данные успешно обновлены"}


@router.put("/update_avatar")
async def user_update_avatar(user: UserDep, file: UploadFile):
    upload = await upload_handler.upload(file)
    user.avatar = upload
    try:
        await user.save()
        return {"status": "success", "message": "Аватарка успешно обновлена!"}
    except exs.IntegrityError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Произошла неожиданная ошибка")


@router.put("/update_password")
async def user_update_password(user: UserDep, current_password: str, new_password: str):
    if user.password != User.crypt_password(current_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Неверный пароль")
    try:
        # Если обновляем пароль, то чистим кэш
        await user.clear_cache()
        user.password = User.crypt_password(new_password)
        # !!! Пользователь вылетит, так как его токен станет невалидным!
        await user.save()
        return {"status": "success", "message": "Пароль успешно обновлён!"}
    except exs.IntegrityError or exs.ValidationError:
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
        "rating": user.rating
    }


@router.get("/user_info")
async def get_info(user_id: int):
    try:
        user = await User.get(id=user_id)
        return {
            "id": user.id,
            "email": user.email,
            "nickname": user.nickname,
            "rating": user.rating
        }
    except exs.DoesNotExist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)


@router.get("/get_cent_token")
async def get_centrifugo_token(user: UserDep):
    return await get_cent_token(user.id)


# TODO: Добавить возможность авторизации через SSO
