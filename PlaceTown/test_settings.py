from .settings import *

DEBUG = True

ALLOWED_HOSTS = []

STATIC_ROOT = None

STATICFILES_DIRS = [
    os.path.join(BASE_DIR, "static"),
]

DJANGO_TELEGRAMBOT = {

    'MODE': 'POLLING',
    'BOTS': [
        {
           'TOKEN': '1262324815:AAFdunNCwz7S2mG_nnFrVxfSIDl1o8ONx0g',
        },
    ],
}
