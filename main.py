import logging

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from tortoise.contrib.fastapi import register_tortoise

from handlers.CacheHandler import mc
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
from routes.notification import router as notification_router

logging.basicConfig(level=logging.INFO)
app = FastAPI()
app.include_router(user_router, prefix="/user")
app.include_router(moment_router, prefix="/moment")
app.include_router(subscription_router, prefix="/subscription")
app.include_router(like_router, prefix="/like")
app.include_router(comment_router, prefix="/comment")
app.include_router(notification_router, prefix="/notification")

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
        'models.Notification',
    ]},
    generate_schemas=True,
    add_exception_handlers=True,
)
origins = [
    "http://localhost",
    "http://localhost:8000",
    "http://localhost:3000",
]

# лучше не использовать такие настройки в проде
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    pass


@app.on_event("shutdown")
async def shutdown_event():
    upload_handler.close()
    mc.close()
