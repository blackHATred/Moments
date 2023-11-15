import random

import pytest
from httpx import AsyncClient
from tortoise import Tortoise

from main import app

# Для тестов можно использовать sqlite прям в оперативке
DB_URL = "sqlite://:memory:"


async def init_db(db_url, create_db: bool = False, schemas: bool = False) -> None:
    """Инициализация БД для тестов"""
    await Tortoise.init(
        db_url=db_url, modules={'models': [
            'models.Comment',
            'models.CommentLike',
            'models.Moment',
            'models.MomentLike',
            'models.Subscription',
            'models.Tag',
            'models.Upload',
            'models.User',
            'models.TagMoment',
        ]}, _create_db=create_db
    )
    if create_db:
        print(f"БД создана")
    if schemas:
        await Tortoise.generate_schemas()
        print("Схемы успешно сгенерированы")


async def init(db_url: str = DB_URL):
    await init_db(db_url, True, True)


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.fixture(scope="session")
async def client():
    async with AsyncClient(app=app, base_url="http://test") as client:
        print("Клиент готов")
        yield client


@pytest.fixture(scope="session", autouse=True)
async def initialize_tests():
    await init()
    yield
    await Tortoise._drop_databases()


# База пользователей для примера
users = [{"email": f"{i}@test.com", "nickname": f"test_user{i}", "password": "Qwerty12345!"} for i in range(100)]
# Пользователь, вокруг которого будут вертеться основные тесты
user = {"email": "test@test.com", "nickname": "test_user", "password": "Qwerty12345!"}


@pytest.mark.anyio
async def test_user_default_flow(client: AsyncClient):
    """
    Проверяем стандартный флоу пользователя
    :param client: клиент для взаимодействия с FastAPI
    """
    # Регистрируем пользователя
    response = await client.post(
        "/user/register",
        params=user
    )
    assert response.status_code == 200
    assert response.json() == {"status": "success", "message": "Пользователь успешно создан"}

    # Входим
    response = await client.post(
        "/user/login",
        # В качестве логина возьмём наугад email или nickname
        params={"login": random.choice((user["email"], user["nickname"])), "password": user["password"]}
    )
    assert response.status_code == 200
    # Сохраним токен нашего пользователя
    token = response.json()["token"]

    # Получим токен от centrifugo
    response = await client.get(
        "/user/get_cent_token",
        # В качестве логина возьмём наугад email или nickname
        params={"token": token}
    )
    assert response.status_code == 200
    # Сохраним токен centrifugo нашего пользователя
    cent_token = response.json()["token"]

    # Получаем инфу о себе
    response = await client.get(
        "/user/my_info",
        params={"token": token}
    )
    assert response.status_code == 200
    assert response.json() == {"id": 1,
                               "email": "test@test.com",
                               "nickname": "test_user",
                               "rating": 0}

    # Обновим инфу о себе
    response = await client.put(
        "/user/update_info",
        params={"token": token, "email": "test_temp@test.com", "nickname": "test_user_temp"}
    )
    assert response.status_code == 200
    # Ещё раз получим инфу о себе
    response = await client.get(
        "/user/my_info",
        params={"token": token}
    )
    assert response.status_code == 200
    assert response.json() == {"id": 1,
                               "email": "test_temp@test.com",
                               "nickname": "test_user_temp",
                               "rating": 0}
    user["email"] = "test_temp@test.com"
    user["nickname"] = "test_user_temp"

    # получаем свою аватарку (дефолтную)
    response = await client.get(
        "/user/avatar",
        params={"user_id": 1}
    )
    assert response.status_code == 307  # должен вернуться редирект на фотку

    # обновим свою аватарку
    with open("assets/avatar.jpg", "rb") as data:
        response = await client.put(
            "/user/update_avatar",
            params={"token": token},
            files={"file": data.read()}
        )
    assert response.status_code == 200  # должен вернуться редирект на фотку
    assert response.json() == {"status": "success", "message": "Аватарка успешно обновлена!"}

    # ещё раз получаем свою аватарку (на этот раз загруженную)
    response = await client.get(
        "/user/avatar",
        params={"user_id": 1}
    )
    assert response.status_code == 307  # должен вернуться редирект на фотку

    # обновим пароль
    response = await client.put(
        "/user/update_password",
        params={"token": token, "current_password": user["password"], "new_password": user["password"]+"!"}
    )
    print(response.text)
    assert response.status_code == 200
    user["password"] = user["password"]+"!"

    # Обновили пароль - сессия вылетела. Получим новый токен
    response = await client.post(
        "/user/login",
        # В качестве логина возьмём наугад email или nickname
        params={"login": random.choice((user["email"], user["nickname"])), "password": user["password"]}
    )
    assert response.status_code == 200
    # Сохраним токен нашего пользователя
    token = response.json()["token"]

    # Зарегистрируем пустышки
    for us in users:
        await client.post("/user/register", params=us)

    # Получим информацию о любом из них
    target_id = random.randint(2, 101)
    response = await client.get(
        "/user/user_info",
        params={"user_id": target_id}
    )
    assert response.status_code == 200
    assert response.json() == {"id": target_id, "rating": 0,
                               "email": users[target_id-2]["email"], "nickname": users[target_id-2]["nickname"]}
