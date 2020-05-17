from django.db import models
from django.utils.translation import gettext as _
from telegram import Bot, Update
from telegram.ext import MessageHandler

from backend.bot import filters as bot_filters, keyboards
from backend.bot.handlers import callbacks
from backend.models import TelegramUser, Category


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

    def callback(self, bot: Bot, update: Update, user: TelegramUser):
        raise NotImplementedError


class CategoriesMessages(BaseMessageHandler):
    FILTERS = bot_filters.RegexFilter('^', 'categories')

    def callback(self, bot: Bot, update: Update, user: TelegramUser):
        from backend.bot import pagination

        categories = Category.objects.annotate(cid=models.F('id')).values('cid', 'name')
        if not categories:

            update.effective_message.reply_text(_('not_choose_categories'), reply_markup=keyboards.main_menu())
            return False

        paginator = pagination.CallbackPaginator(
            categories, callback=callbacks.InstitutionCallback,
            page_callback=callbacks.CategoriesCallback, callback_data_keys=['cid']
        )
        update.effective_message.reply_text(_('choose_category'), reply_markup=paginator.inline_markup)
