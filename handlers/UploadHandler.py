import logging
from uuid import uuid4

import boto3
import botocore.exceptions as exs
from fastapi import UploadFile
from tortoise.backends.base.client import TransactionContext

try:
    from config import s3_config, db_url, s3_cors_configuration
except ModuleNotFoundError:
    from config_example import s3_config, db_url, s3_cors_configuration

from models.Upload import Upload


class UploadHandler:
    def __init__(self):
        self.session = boto3.session.Session()
        self.s3_client = self.session.client(**s3_config)
        self.s3_client.put_bucket_cors(Bucket='moments_uploads', CORSConfiguration=s3_cors_configuration)
        try:
            self.s3_client.head_object(Bucket='moments_uploads', Key="avatar.jpg")
        except exs.ClientError:
            with open('assets/avatar.jpg', 'rb') as data:
                self.s3_client.upload_fileobj(data, 'moments_uploads', "avatar.jpg")
        logging.info("S3 инициализирован")

    def close(self):
        """
        Закрывает сессию с S3
        :return:
        """
        self.s3_client.close()
        logging.info("Соединение с S3 закрыто")

    async def upload(self, upload_file: UploadFile, connection: TransactionContext | None = None) -> Upload:
        """
        Загружает файл в S3 хранилище
        :param upload_file: объект загруженного файла из FastAPI
        :param connection: подключение, которое следует использовать (указание на транзакцию извне этой функции)
        :return: объект загруженного пользователем файла
        """
        uuid = uuid4()
        upload = await Upload.create(filename=f"{uuid}{upload_file.filename[upload_file.filename.rfind('.'):]}",
                                     using_db=connection)
        # Загрузка файла в S3
        try:
            self.s3_client.upload_fileobj(upload_file.file, 'moments_uploads', upload.filename)
        except exs.ClientError as e:
            # Если проблема с S3, то логируем и поднимаем ошибку
            logging.error(e, exc_info=True)
            raise
        return upload

    def download(self, upload: Upload) -> str:
        """
        Возвращает ссылку для скачивания файла из S3 хранилища
        :param upload: объект загруженного пользователем файла
        :return: ссылка для скачивания файла
        """
        # Время действия ссылки ограничено сервером S3
        return self.s3_client.generate_presigned_url('get_object',
                                                     {'Bucket': 'moments_uploads', 'Key': upload.filename})

    def download_default_avatar(self) -> str:
        return self.s3_client.generate_presigned_url('get_object',
                                                     {'Bucket': 'moments_uploads', 'Key': "avatar.jpg"})


# обработчик загрузок
upload_handler = UploadHandler()
