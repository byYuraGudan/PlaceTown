import logging

from django.utils.translation import gettext as _, ugettext_lazy
from telegram import Update, Bot
from telegram.ext import CallbackQueryHandler

from backend.models import TelegramUser

log = logging.getLogger(__name__)


class BaseCallbackQueryHandler(CallbackQueryHandler):
    PATTERN = None
    MANAGER = None

    def __init__(self, *args, **kwargs):
        if self.PATTERN is None:
            raise AttributeError('Key must be not None.')
        pattern = '^{};+'.format(self.PATTERN)
        super(BaseCallbackQueryHandler, self).__init__(self.callback, *args, pattern=pattern, **kwargs)

    def collect_optional_args(self, dispatcher, update=None, check_result=None):
        args = super(BaseCallbackQueryHandler, self).collect_optional_args(dispatcher, update, check_result)
        if update:
            args['user'] = TelegramUser.get_user(update.callback_query.from_user)
            args['data'] = self.get_data(update.callback_query.data)
        else:
            args['user'] = None
            args['data'] = None
        return args

    def callback(self, bot: Bot, update: Update, user: TelegramUser, data):
        raise NotImplementedError

    @classmethod
    def set_data(cls, **kwargs):
        data = list('{}={}'.format(key, value) for key, value in kwargs.items())
        return f'{cls.PATTERN};{";".join(data)}'

    @staticmethod
    def get_data(data):
        data = [item.split('=') for item in filter(bool, data.split(';')[1:])]
        return {key: int(value) if key.endswith(('id', 'use', 'back_data')) else value for key, value in data}


class LanguageCallback(BaseCallbackQueryHandler):
    LANGUAGE = {
        'uk': ugettext_lazy('Ukrainian'),
        'en': ugettext_lazy('English'),
        'ru': ugettext_lazy('Russian'),
    }
    PATTERN = 'lang'

    def callback(self, bot, update, user, data):
        query = update.callback_query
        user.lang = data.get('lang')
        user.save()
        query.edit_message_text(_('your_lang').format(self.LANGUAGE.get(data.get('lang'))))
        log.debug(f'User{user} change language {user.lang}')
