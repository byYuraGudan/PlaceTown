import logging

from django.conf import settings
from django.db import models
from django.utils.translation import gettext as _, activate
from telegram import Update, Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler, run_async

from backend.bot import keyboards
from backend.models import TelegramUser, Category, Institution

log = logging.getLogger(__name__)


class BaseCallbackQueryHandler(CallbackQueryHandler):
    PATTERN = None

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

    def callback(self, bot: Bot, update: Update, user: TelegramUser, data: dict):
        raise NotImplementedError

    @classmethod
    def set_data(cls, **kwargs):
        data = list('{}={}'.format(key, value) for key, value in kwargs.items())
        return f'{cls.PATTERN};{";".join(data)}'

    @staticmethod
    def get_data(data):
        data = [item.split('=') for item in filter(bool, data.split(';')[1:])]
        return {key: int(value) if key.endswith(('id', 'use', 'back_data', 'page')) else value for key, value in data}


class LanguageCallback(BaseCallbackQueryHandler):
    LANGUAGES = dict(settings.LANGUAGES)
    PATTERN = 'lang'

    def callback(self, bot: Bot, update: Update, user: TelegramUser, data: dict):
        query = update.callback_query
        user.lang = data.get('lang')
        user.save()
        activate(user.lang)
        query.edit_message_text(_('your_lang').format(self.LANGUAGES.get(data.get('lang'))))
        update.effective_message.reply_text(_('select_you_interested'), reply_markup=keyboards.main_menu())


class InstitutionDetailCallback(BaseCallbackQueryHandler):
    PATTERN = 'iid'

    def callback(self, bot: Bot, update: Update, user: TelegramUser, data: dict):
        query = update.callback_query

        detail = Institution.objects.filter(id=data.get('id')).first()
        if not detail:
            query.edit_message_text(_('not_info_about_institution'))
            return False
        keyboard = []
        markup = None
        if detail.site:
            keyboard.append(InlineKeyboardButton(_('site_url'), url=detail.site))
            from backend.bot.keyboards import build_menu
            markup = InlineKeyboardMarkup(build_menu(keyboard, cols=1))
        query.edit_message_text(user.get_text('about_institution').format(**detail.__dict__), reply_markup=markup)


class InstitutionCallback(BaseCallbackQueryHandler):
    PATTERN = 'pid'

    @run_async
    def callback(self, bot: Bot, update: Update, user: TelegramUser, data: dict):
        query = update.callback_query
        from backend.bot import pagination
        details = Institution.objects.filter(category=data.get('cid')).values('id', 'name').order_by('-id')

        if not details:
            query.edit_message_text(
                user.get_text('not_choose_performer_for_current_category'),
                reply_markup=query.message.reply_markup
            )
            return False

        paginator = pagination.CallbackPaginator(
            details, callback=InstitutionDetailCallback, page_callback=self,
            page=data.get('page', 1), callback_data_keys=['id'],
        )
        query.edit_message_text(user.get_text('choose_institution'), reply_markup=paginator.inline_markup)


class CategoriesCallback(BaseCallbackQueryHandler):
    PATTERN = 'cid'

    @run_async
    def callback(self, bot: Bot, update: Update, user: TelegramUser, data: dict):
        query = update.callback_query
        from backend.bot import pagination
        categories = Category.objects.annotate(cid=models.F('id')).values('cid', 'name')

        if not categories:
            query.edit_message_text(_('not_choose_categories'))
            return False

        paginator = pagination.CallbackPaginator(
            categories, callback=InstitutionCallback, page_callback=self, page=data.get('page', 1),
            callback_data_keys=['cid']
        )
        query.edit_message_text(_('choose_category'), reply_markup=paginator.inline_markup)
