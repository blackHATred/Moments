import random

import pytest
from faker import Faker
from httpx import AsyncClient
from tortoise import Tortoise

from handlers.CacheHandler import mc
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
            'models.Notification',
        ]}, _create_db=create_db
    )
    if create_db:
        print(f"БД создана")
    if schemas:
        await Tortoise.generate_schemas()
        print("Схемы успешно сгенерированы")
    # Чистим весь кэш для чистоты эксперимента
    mc.flush_all()


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
            files={"file": data}
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


@pytest.mark.anyio
async def test_user_bad_flow(client: AsyncClient):
    """
    Проверяем нестандартный флоу пользователя
    :param client: клиент для взаимодействия с FastAPI
    """
    # Зарегистрируем пользователя с невалидной почтой
    response = await client.post(
        "/user/register",
        params={"email": "ne_email", "password": "Qwerty123!", "nickname": "testing"}
    )
    assert response.status_code == 400
    # Зарегистрируем пользователя с невалидным паролем
    response = await client.post(
        "/user/register",
        params={"email": "email@gmail.com", "password": "qwerty123", "nickname": "testing"}
    )
    assert response.status_code == 400


@pytest.mark.anyio
async def test_subscriptions(client: AsyncClient):
    """
    Проверяем стандартный флоу подписок
    :param client: клиент для взаимодействия с FastAPI
    """
    # Войдём в первый аккаунт
    response = await client.post(
        "/user/login",
        # В качестве логина возьмём наугад email или nickname
        params={"login": random.choice((users[0]["email"], users[0]["nickname"])), "password": users[0]["password"]}
    )
    # Сохраним токен нашего пользователя
    token = response.json()["token"]

    # Подпишемся на 10 пользователей
    for i in range(10, 20):
        response = await client.post(
            "/subscription/subscribe",
            # В качестве логина возьмём наугад email или nickname
            params={"token": token, "author_id": i}
        )
        assert response.status_code == 200
    # Отпишемся от одного из пользователей
    response = await client.post(
        "/subscription/unsubscribe",
        params={"token": token, "author_id": 10}
    )
    assert response.status_code == 200
    response = await client.get(
        "/subscription/my_subscriptions",
        params={"token": token}
    )
    assert response.status_code == 200
    # Теперь в нашем списке подписок должно быть 9 авторов
    assert len(response.json()["subscriptions"]) == 9


@pytest.mark.anyio
async def test_moments(client: AsyncClient):
    """
    Проверяем стандартный флоу моментов
    :param client: клиент для взаимодействия с FastAPI
    """
    # Войдём в первый аккаунт
    response = await client.post(
        "/user/login",
        # В качестве логина возьмём наугад email или nickname
        params={"login": random.choice((users[0]["email"], users[0]["nickname"])), "password": users[0]["password"]}
    )
    # Сохраним токен нашего пользователя
    token = response.json()["token"]

    # Создадим момент
    with open("assets/avatar.jpg", "rb") as data:
        response = await client.post(
            "/moment/create",
            params={"token": token,
                    "title": "Мой первый пост!",
                    "description": "Ставлю хэштеги #HelloWorld и #test и не забываю упомянуть @test_user10, "
                                   "чтобы ему пришло от меня уведомление!"},
            files={"file": data}
        )
    assert response.status_code == 200
    assert response.json() == {"status": "success", "message": "Момент успешно создан"}

    # Получим изображение, прикреплённое к только что созданному моменту
    response = await client.get(
        "/moment/picture",
        params={"moment_id": 1}
    )
    assert response.status_code == 307  # должен вернуться редирект на фотку

    # Получим информацию о моменте
    response = await client.get(
        "/moment/info",
        params={"moment_id": 1}
    )
    assert response.status_code == 200
    assert response.json() == {
        "title": "Мой первый пост!",
        "description": 'Ставлю хэштеги #HelloWorld и #test и не забываю упомянуть <a href="/user/12">@test_user10,</a> '
                       'чтобы ему пришло от меня уведомление!',
        "likes": 0,
        "views": 1,  # Т.к. при создании этого запроса мы автоматически прибавили один просмотр
        "tags": ["helloworld", "test"],
        "comments": 0
    }

    # Попробуем обновить пост, изменив заголовок
    response = await client.put(
        "/moment/update",
        params={"token": token, "moment_id": 1, "title": "Обновлённый заголовок"}
    )
    assert response.status_code == 200
    assert response.json() == {"status": "success", "message": "Момент успешно изменён"}

    # Повторно получим информацию о моменте и увидим новый заголовок
    response = await client.get(
        "/moment/info",
        params={"moment_id": 1}
    )
    assert response.status_code == 200
    assert response.json()["title"] == "Обновлённый заголовок"

    # Получим все свои моменты
    response = await client.get(
        "/moment/user_moments",
        params={"user_id": 2}
    )
    assert response.status_code == 200
    assert response.json()["moments"] == [1]

    # Найдем свой момент по использованному в нём хэштегу
    response = await client.get(
        "/moment/tag_search",
        params={"tag": "helloworld"}
    )
    assert response.status_code == 200
    assert response.json()["moments"] == [1]

    # Зайдём со стороны другого пользователя, подпишемся и посмотрим свою ленту.
    # Заходим из-под третьего пользователя
    response = await client.post(
        "/user/login",
        # В качестве логина возьмём наугад email или nickname
        params={"login": random.choice((users[1]["email"], users[1]["nickname"])), "password": users[1]["password"]}
    )
    # Сохраним токен нашего пользователя
    token1 = response.json()["token"]
    # Подпишемся на второго
    await client.post(
        "/subscription/subscribe",
        params={"token": token1, "author_id": 2}
    )
    # А теперь смотрим свою ленту
    response = await client.get(
        "/moment/last_moments",
        params={"token": token1}
    )
    assert response.status_code == 200
    assert response.json()["moments"] == [1]

    # Напоследок удаляем пост
    response = await client.delete(
        "/moment/delete",
        params={"token": token, "moment_id": 1}
    )
    print(response.text)
    assert response.status_code == 200
    assert response.json() == {"status": "success", "message": "Момент успешно удалён"}

    # Создадим момент, чтобы использовать его в последующих тестах
    with open("assets/avatar.jpg", "rb") as data:
        response = await client.post(
            "/moment/create",
            params={"token": token,
                    "title": "Мой первый пост!",
                    "description": "Ставлю хэштеги #HelloWorld и #test и не забываю упомянуть @test_user10, "
                                   "чтобы ему пришло от меня уведомление!"},
            files={"file": data}
        )


@pytest.mark.anyio
async def test_comments(client: AsyncClient):
    """
    Проверяем стандартный флоу комментариев
    :param client: клиент для взаимодействия с FastAPI
    """
    # Войдём в аккаунт
    response = await client.post(
        "/user/login",
        params={"login": random.choice((users[10]["email"], users[10]["nickname"])), "password": users[10]["password"]}
    )
    # Сохраним токен нашего пользователя
    token = response.json()["token"]

    # Создадим комментарий
    response = await client.post(
        "/comment/create",
        params={"token": token, "moment_id": 2, "text": "Кукож"}
    )
    assert response.status_code == 200
    assert response.json() == {"status": "success", "message": "Комментарий успешно отправлен"}

    # Получим свой комментарий под моментом
    response = await client.get(
        "/comment/my_comment",
        params={"token": token, "moment_id": 2}
    )
    assert response.status_code == 200
    assert response.json() == {"comment": 1}

    # Изменим текст комментария
    response = await client.put(
        "/comment/update",
        params={"token": token, "comment_id": 1, "text": "Новый текст комментария"}
    )
    assert response.status_code == 200
    assert response.json() == {"status": "success", "message": "Комментарий успешно обновлён"}

    # Получим все комментарии под моментом
    response = await client.get(
        "/comment/get_comments",
        params={"moment_id": 2}
    )
    assert response.status_code == 200
    assert response.json() == {"comments": [1]}

    # Прочитаем комментарий
    response = await client.get(
        "/comment/get_comment",
        params={"comment_id": 1}
    )
    assert response.status_code == 200
    assert response.json() == {"author": 12, "text": "Новый текст комментария", "likes": 0}

    # Попробуем удалить комментарий
    response = await client.delete(
        "/comment/delete",
        params={"token": token, "comment_id": 1}
    )
    assert response.status_code == 200
    assert response.json() == {"status": "success", "message": "Комментарий успешно удалён"}

    # Напоследок ещё раз создадим комментарий для последующих тестов
    response = await client.post(
        "/comment/create",
        params={"token": token, "moment_id": 2, "text": "Кукож"}
    )
    assert response.status_code == 200
    assert response.json() == {"status": "success", "message": "Комментарий успешно отправлен"}


@pytest.mark.anyio
async def test_likes(client: AsyncClient):
    """
    Проверяем стандартный флоу лайков
    :param client: клиент для взаимодействия с FastAPI
    """
    # Войдём в аккаунт
    response = await client.post(
        "/user/login",
        params={"login": random.choice((users[1]["email"], users[1]["nickname"])), "password": users[1]["password"]}
    )
    # Сохраним токен нашего пользователя
    token = response.json()["token"]

    # Поставим лайк на момент
    response = await client.post(
        "/like/like_moment",
        params={"token": token, "moment_id": 2}
    )
    assert response.status_code == 200
    assert response.json() == {"status": "success", "message": "Лайк на момент успешно поставлен"}

    # Проверим, действительно ли мы лайкнули
    response = await client.get(
        "/like/is_moment_liked",
        params={"token": token, "moment_id": 2}
    )
    assert response.status_code == 200
    assert response.json() == {"liked": True}

    # Уберём лайк
    response = await client.post(
        "/like/unlike_moment",
        params={"token": token, "moment_id": 2}
    )
    assert response.status_code == 200
    assert response.json() == {"status": "success", "message": "Лайк успешно убран"}

    # Ещё раз проверим наличие лайка
    response = await client.get(
        "/like/is_moment_liked",
        params={"token": token, "moment_id": 2}
    )
    assert response.status_code == 200
    assert response.json() == {"liked": False}

    # Поставим лайк на комментарий
    response = await client.post(
        "/like/like_comment",
        params={"token": token, "comment_id": 2}
    )
    assert response.status_code == 200
    assert response.json() == {"status": "success", "message": "Лайк на комментарий успешно поставлен"}

    # Проверим, действительно ли мы лайкнули
    response = await client.get(
        "/like/is_comment_liked",
        params={"token": token, "comment_id": 2}
    )
    assert response.status_code == 200
    assert response.json() == {"liked": True}

    # Уберём лайк
    response = await client.post(
        "/like/unlike_comment",
        params={"token": token, "comment_id": 2}
    )
    assert response.status_code == 200
    assert response.json() == {"status": "success", "message": "Лайк успешно убран"}

    # Ещё раз проверим наличие лайка
    response = await client.get(
        "/like/is_comment_liked",
        params={"token": token, "comment_id": 2}
    )
    assert response.status_code == 200
    assert response.json() == {"liked": False}


@pytest.mark.anyio
async def test_notifications(client: AsyncClient):
    """
    Проверяем стандартный флоу уведомлений
    :param client: клиент для взаимодействия с FastAPI
    """
    # Войдём в аккаунт, на который должны были прийти уведомления в ходе предыдущих тестов
    response = await client.post(
        "/user/login",
        # В качестве логина возьмём наугад email или nickname
        params={"login": random.choice((users[10]["email"], users[10]["nickname"])), "password": users[10]["password"]}
    )
    # Сохраним токен нашего пользователя
    token = response.json()["token"]

    # Предположим, что мы получили уведомление по centrifugo. Теперь мы хотим получить его содержимое
    response = await client.get(
        "/notification/get",
        params={"token": token, "notification_id": 1}
    )
    assert response.status_code == 200
    assert len(response.json()['notification']) > 1


@pytest.mark.anyio
async def test_mass_create(client: AsyncClient):
    """
    Проверяем работу под нагрузкой
    :param client: клиент для взаимодействия с FastAPI
    """
    Faker.seed(0)
    fake = Faker()

    # Создадим 10к пользователей
    profiles = [fake.simple_profile() for _ in range(10000)]
    for profile in profiles:
        # Регистрируем пользователя
        response = await client.post(
            "/user/register",
            params={"email": profile["mail"], "nickname": profile["username"], "password": "Qwerty!123"}
        )
        if response.status_code == 200:
            assert response.json() == {"status": "success", "message": "Пользователь успешно создан"}
            r = await client.post(
                "/user/login",
                params={"login": profile["username"], "password": "Qwerty!123"}
            )
            profile["token"] = r.json()["token"]
        else:
            # Фейкер может случайно сгенерировать повторяющиеся профили
            assert response.json() == {"detail": r"Пользователь с такой почтой и\или никнеймом уже существует"}
    # Не будем учитывать профили, которые не смогли зарегистрировать из-за дублирования данных
    profiles = [profile for profile in profiles if "token" in profile]
    # Выведем итоговое кол-во созданных пользователей
    print(len(profiles))

    # Чтобы не нагружать S3 и не тратить баланс в облаке, ограничимся 100 моментами
    with open("assets/avatar.jpg", "rb") as data:
        for _ in range(100):
            response = await client.post(
                "/moment/create",
                params={"token": random.choice(profiles).get("token"),
                        "title": fake.sentence(nb_words=10),
                        "description": fake.paragraph(nb_sentences=2)},
                files={"file": data}
            )
            assert response.status_code == 200
            assert response.json() == {"status": "success", "message": "Момент успешно создан"}

    # От имени каждого пользователя оставим комментарий на случайные моменты (чуть меньше 10к комментариев)
    for profile in profiles:
        response = await client.post(
            "/comment/create",
            params={"token": profile.get("token"),
                    "moment_id": random.randint(5, 101),
                    "text": fake.paragraph(nb_sentences=2)}
        )
        assert response.status_code == 200
        assert response.json() == {"status": "success", "message": "Комментарий успешно отправлен"}

    # От имени каждого пользователя поставим лайки на случайные комментарии и моменты (выйдет чуть меньше 20к лайков)
    for profile in profiles:
        response = await client.post(
            "/like/like_moment",
            params={"token": profile.get("token"), "moment_id": random.randint(5, 101)}
        )
        assert response.status_code == 200
        assert response.json() == {"status": "success", "message": "Лайк на момент успешно поставлен"}

        response = await client.post(
            "/like/like_comment",
            params={"token": profile.get("token"), "comment_id": random.randint(5, len(profiles))}
        )
        assert response.status_code == 200
        assert response.json() == {"status": "success", "message": "Лайк на комментарий успешно поставлен"}
