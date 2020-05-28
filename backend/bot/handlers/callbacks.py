import logging

from django.conf import settings
from django.db import models
from django.utils.translation import gettext as _, activate
from telegram import Update, Bot, InlineKeyboardButton, InlineKeyboardMarkup, ParseMode
from telegram.ext import CallbackQueryHandler

from backend.bot import keyboards
from backend.models import TelegramUser, Category, Company

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


class CompanyLocationCallback(BaseCallbackQueryHandler):
    PATTERN = 'location'

    def callback(self, bot: Bot, update: Update, user: TelegramUser, data: dict):
        company = Company.objects.filter(id=data.get('company_id')).first()
        if not company:
            update.effective_message.reply_text(_('company_doesnt_exists'))
            return
        if not company.latitude and company.longitude:
            update.effective_message.reply_text(_('company_has_not_info_location'))
            return
        message = update.effective_message.reply_location(company.longitude, company.latitude)
        update.effective_message.reply_text(
            _('location_of_company').format(name=company.name),
            reply_to_message_id=message.message_id
        )


class CompanyDetailCallback(BaseCallbackQueryHandler):
    PATTERN = 'did'

    def callback(self, bot: Bot, update: Update, user: TelegramUser, data: dict):
        user.activate()
        query = update.callback_query

        company = Company.objects.filter(id=data.get('id')).first()
        if not company:
            query.edit_message_text(_('not_info_about_company'))
            return False

        keyboard, markup = [], None

        if company.site:
            keyboard.append(InlineKeyboardButton(_('site_url'), url=company.site))

        if company.longitude and company.latitude:
            callback = CompanyLocationCallback.set_data(company_id=company.id)
            keyboard.append(InlineKeyboardButton(_('location'), callback_data=callback))

        if keyboard:
            from backend.bot.keyboards import build_menu
            markup = InlineKeyboardMarkup(build_menu(keyboard, cols=1))

        text = _('about_company').format(name=company.name, description=company.description or _('no_info_available'))

        if company.address:
            text += f"\n🏢: {company.address}"
        if company.contact:
            text += f"\n📞: {company.contact}"
        if company.email:
            text += f"\n📧: {company.email}"

        query.edit_message_text(text, reply_markup=markup, parse_mode=ParseMode.MARKDOWN)


class CompaniesCallback(BaseCallbackQueryHandler):
    PATTERN = 'iid'

    def callback(self, bot: Bot, update: Update, user: TelegramUser, data: dict):
        user.activate()
        query = update.callback_query
        from backend.bot import pagination
        companies = Company.objects.filter(category_id=data.get('cid')).values('id', 'name').order_by('-id')
        if not companies:
            query.edit_message_text(
                _('not_choose_performer_for_current_category'),
                reply_markup=query.message.reply_markup
            )
            return False

        paginator = pagination.CallbackPaginator(
            companies, callback=CompanyDetailCallback, page_callback=self,
            page=data.get('page', 1), callback_data_keys=['id'],
        )
        query.edit_message_text(_('choose_company'), reply_markup=paginator.inline_markup)


class CategoriesCallback(BaseCallbackQueryHandler):
    PATTERN = 'cid'

    def callback(self, bot: Bot, update: Update, user: TelegramUser, data: dict):
        query = update.callback_query
        from backend.bot import pagination
        categories = Category.objects.annotate(cid=models.F('id')).values('cid', 'name')
        if not categories:
            query.edit_message_text(_('not_choose_categories'))
            return False

        paginator = pagination.CallbackPaginator(
            categories, callback=CompaniesCallback, page_callback=self, page=data.get('page', 1),
            callback_data_keys=['cid']
        )
        query.edit_message_text(_('choose_category'), reply_markup=paginator.inline_markup)
