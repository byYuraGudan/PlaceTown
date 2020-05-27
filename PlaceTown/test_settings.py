from .settings import *

DEBUG = True

ALLOWED_HOSTS = []

DJANGO_TELEGRAMBOT = {

    'MODE': 'POLLING',
    'BOTS': [
        {
           'TOKEN': '1262324815:AAFdunNCwz7S2mG_nnFrVxfSIDl1o8ONx0g',
           'ASYNC_WORKERS': 4,
           'CONTEXT': True,
        },
    ],
}
