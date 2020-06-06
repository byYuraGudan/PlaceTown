import logging

from django.utils.translation import gettext as _
from telegram import Bot, Update, InlineKeyboardButton as InlKeyBtn, InlineKeyboardMarkup as InlKeyMark
from telegram.ext import CommandHandler

from backend.bot import keyboards
from backend.bot.handlers import callbacks
from backend.models import TelegramUser

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

    def callback(self, bot: Bot, update: Update, user: TelegramUser):
        raise NotImplementedError


class HelpCommand(BaseCommandHandler):
    COMMAND = 'help'

    def callback(self, bot: Bot, update: Update, user: TelegramUser):
        update.effective_message.reply_text(_('help'))


class StartCommand(BaseCommandHandler):
    COMMAND = 'start'

    def callback(self, bot: Bot, update: Update, user: TelegramUser):
        update.effective_message.reply_text(_('start').format(user.full_name), reply_markup=keyboards.main_menu(user))


class SettingsCommand(BaseCommandHandler):
    COMMAND = 'settings'

    def callback(self, bot: Bot, update: Update, user: TelegramUser):
        update.effective_message.reply_text(_('settings'), reply_markup=keyboards.settings_markup(user))


class ProfileCommand(BaseCommandHandler):
    COMMAND = 'profile'

    def callback(self, bot: Bot, update: Update, user: TelegramUser):
        if not hasattr(user, 'profile'):
            markup = InlKeyMark(keyboards.build_menu([
                InlKeyBtn(_('create_profile'), callback_data=callbacks.ProfileCreateCallback.set_data()),
            ]))
            update.effective_message.reply_text(_('profile_does_not_exists'), reply_markup=markup)
        else:
            update.effective_message.reply_text(_('profile_exists'), reply_markup=keyboards.site_btn())


class LanguageCommand(BaseCommandHandler):
    COMMAND = 'lang'

    def callback(self, bot: Bot, update: Update, user: TelegramUser):
        update.effective_message.reply_text(_('choose_lang'), reply_markup=keyboards.language(user))


class FilterCommand(BaseCommandHandler):
    COMMAND = 'filter'

    def callback(self, bot: Bot, update: Update, user: TelegramUser):
        update.effective_message.reply_text(_('data_filter'), reply_markup=keyboards.filter_markup(user))
