import time

from cent import Client
import jwt

try:
    from config import CENTRIFUGO_API_URL, CENTRIFUGO_API_KEY, CENTRIFUGO_SECRET
except ModuleNotFoundError:
    from config_example import CENTRIFUGO_API_URL, CENTRIFUGO_API_KEY, CENTRIFUGO_SECRET

cent_client = Client(CENTRIFUGO_API_URL, api_key=CENTRIFUGO_API_KEY, timeout=3)


async def get_cent_token(user_id: int) -> dict:
    """
    Позволяет получить токен для подписчика в centrifugo
    :param user_id: айди пользователя
    :return: {"token": token}
    """
    claims = {
        "sub": user_id,
        "exp": int(time.time()) + 24 * 3600,
    }
    token = jwt.encode(claims, CENTRIFUGO_SECRET, algorithm="HS256")
    return {"token": token}
