from telegram.ext import MessageHandler, Filters

from backend.models import TelegramUser


class BaseMessageHandler(MessageHandler):
    FILTERS = None
    STATE = None

    def __init__(self, *args, **kwargs):
        super(BaseMessageHandler, self).__init__(self.FILTERS, self.callback, *args, **kwargs)

    def collect_optional_args(self, dispatcher, update=None, check_result=None):
        args = super(BaseMessageHandler, self).collect_optional_args(dispatcher, update, check_result)
        if update:
            args['user'] = TelegramUser.get_user(update.effective_message.from_user)
        return args

    def callback(self, bot, update, user):
        raise NotImplementedError
