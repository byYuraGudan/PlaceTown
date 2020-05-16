from django.utils.translation import ugettext as _, activate
from telegram.ext import CommandHandler
from backend.models import TelegramUser
import logging

log = logging.getLogger(__name__)


class BaseCommandHandler(CommandHandler):
    COMMAND = None

    def __init__(self, *args, **kwargs):
        super(BaseCommandHandler, self).__init__(self.COMMAND, self.callback, *args, **kwargs)

    def collect_optional_args(self, dispatcher, update=None, check_result=None):
        args = super(BaseCommandHandler, self).collect_optional_args(dispatcher, update, check_result)
        if update:
            args['user'] = TelegramUser.get_user(update.effective_message.from_user)
        return args

    def callback(self, bot, update, user):
        raise NotImplementedError


class HelpCommand(BaseCommandHandler):
    COMMAND = 'help'

    def callback(self, bot, update, user):
        update.effective_message.reply_text(_('help'))


class StartCommand(BaseCommandHandler):
    COMMAND = 'start'

    def callback(self, bot, update, user):
        update.effective_message.reply_text(_('start').format(user.full_name))


class SettingsCommand(BaseCommandHandler):
    COMMAND = 'settings'

    def callback(self, bot, update, user):
        update.effective_message.reply_text(_('settings'))
