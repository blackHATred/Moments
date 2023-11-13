# S3 storage
# Пример был запущен с использованием хранилища S3 от VK Cloud
s3_config = {
    "service_name": 's3',
    "endpoint_url": 'https://hb.vkcs.cloud',
    "aws_access_key_id": '<YOUR_ACCESS_KEY>',
    "aws_secret_access_key": '<YOUR_SECRET_KEY>',
    "region_name": 'ru-msk'
}
# конфигурация CORS для S3
s3_cors_configuration = {
    'CORSRules': [{
        'AllowedHeaders': ['*'],  # <-- Указать домен своего сайта
        'AllowedMethods': ['GET'],
        'AllowedOrigins': ['*'],
        'ExposeHeaders': [],
        'MaxAgeSeconds': 3000  # <-- Указать время действия сгенерированной ссылки
    }]
}
# Ссылка для взаимодействия с БД. Можно юзать sqlite3/postgresql/mysql
db_url = 'sqlite://db.sqlite3'
# Секретный ключ для создания сессий
TOKEN_SECRET_KEY = 'Я нюхаю цветочки и радуюсь жизни'
