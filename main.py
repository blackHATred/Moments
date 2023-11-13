import logging

from fastapi import FastAPI
from tortoise.contrib.fastapi import register_tortoise
from handlers.UploadHandler import upload_handler

try:
    from config import db_url
except ModuleNotFoundError:
    from config_example import db_url

from routes.user import router as user_router
from routes.moment import router as moment_router
from routes.subscription import router as subscription_router
from routes.like import router as like_router
from routes.comment import router as comment_router

logging.basicConfig(level=logging.INFO)
app = FastAPI()
app.include_router(user_router, prefix="/user")
app.include_router(moment_router, prefix="/moment")
app.include_router(subscription_router, prefix="/subscription")
app.include_router(like_router, prefix="/like")
app.include_router(comment_router, prefix="/comment")

# Инициализируем ORM
register_tortoise(
    app,
    db_url=db_url,
    modules={'models': [
        'models.Comment',
        'models.CommentLike',
        'models.Moment',
        'models.MomentLike',
        'models.Subscription',
        'models.Tag',
        'models.Upload',
        'models.User',
        'models.TagMoment',
    ]},
    generate_schemas=True,
    add_exception_handlers=True,
)


@app.on_event("startup")
async def startup_event():
    pass


@app.on_event("shutdown")
async def shutdown_event():
    upload_handler.close()
