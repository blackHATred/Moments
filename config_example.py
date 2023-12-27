import json
import os

# S3 storage
# Пример был запущен с использованием хранилища S3 от VK Cloud
s3_config = {
    "service_name": 's3',
    "endpoint_url": os.getenv("S3_ENDPOINT_URL", 'https://hb.vkcs.cloud'),
    "aws_access_key_id": os.getenv("S3_ACCESS_KEY", '<YOUR_ACCESS_KEY>'),
    "aws_secret_access_key": os.getenv("S3_SECRET_KEY", '<YOUR_SECRET_KEY>'),
    "region_name": os.getenv("S3_REGION", 'ru-msk')
}
# конфигурация CORS для S3
s3_cors_configuration = {
    'CORSRules': [{
        'AllowedHeaders': ['*'],
        'AllowedMethods': ['GET'],
        # Указать домен своего сайта. Хотя можно оставить и так, тогда картинки смогут открываться и на других сайтах
        'AllowedOrigins': ['*'],
        'ExposeHeaders': [],
        # Указать время кэша
        'MaxAgeSeconds': 3000
    }]
}
# Ссылка для взаимодействия с БД. Можно юзать sqlite3/postgresql/mysql
db_url = 'sqlite://db.sqlite3'
# Секретный ключ для хэширования
TOKEN_SECRET_KEY = os.getenv("TOKEN_SECRET_KEY", 'Я нюхаю цветочки и радуюсь жизни')
# Параметры подключения к memcached
memcached_server = ('localhost', 11211)
# Параметры подключения к centrifugo
with open("centrifugo.json", "r") as file:
    cent_config = json.load(file)
    CENTRIFUGO_API_KEY = cent_config.get("api_key")
    CENTRIFUGO_SECRET = cent_config.get("token_hmac_secret_key")
CENTRIFUGO_API_URL = "http://centrifugo:8000/api"
