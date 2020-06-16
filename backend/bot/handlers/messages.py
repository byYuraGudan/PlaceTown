import logging

from django.db import models
from django.utils import timezone
from django.utils.translation import gettext as _
from django_telegrambot.apps import DjangoTelegramBot
from telegram import Bot, Update
from telegram.ext import MessageHandler, Filters

from backend.admin import CompanyAdmin
from backend.bot import filters as bot_filters, keyboards
from backend.bot.handlers import callbacks
from backend.models import TelegramUser, Category, Order, News

logger = logging.getLogger(__name__)


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
            update.effective_message.reply_text(_('not_choose_categories'), reply_markup=keyboards.main_menu(user))
            return False

        paginator = pagination.CallbackPaginator(
            categories, callback=callbacks.CompaniesCallback,
            page_callback=callbacks.CategoriesCallback, callback_data_keys=['cid']
        )
        update.effective_message.reply_text(_('choose_category'), reply_markup=paginator.inline_markup)


class MyProfileMessages(BaseMessageHandler):
    FILTERS = bot_filters.RegexFilter('^', 'my_profile')

    def callback(self, bot: Bot, update: Update, user: TelegramUser):
        update.effective_message.reply_text(_('my_profile_data'), reply_markup=keyboards.profile_markup(user))


class OutgoingOrdersMessage(BaseMessageHandler):
    FILTERS = bot_filters.RegexFilter('^', 'outgoing_orders')

    def callback(self, bot: Bot, update: Update, user: TelegramUser):
        from backend.bot import pagination
        orders = Order.objects.filter(customer=user) \
            .exclude(status__in=user.order_filter_status) \
            .values('id', 'status', 'service__name') \
            .order_by('-updated')

        if not orders:
            update.effective_message.reply_text(_('not_info_about_available_orders'))
            return False

        paginator = pagination.CallbackPaginator(
            orders, callback=callbacks.OutgoingOrderDetailCallback, page_callback=callbacks.OutgoingOrderCallback,
            title_pattern=lambda x: f"{Order.STATUS_EMOJI_DICT.get(x['status'])} {x['service__name']}",
            callback_data_keys=['id'],
        )
        update.effective_message.reply_text(_('choose_order'), reply_markup=paginator.inline_markup)


class LocationMessages(BaseMessageHandler):
    FILTERS = Filters.location

    def callback(self, bot: Bot, update: Update, user: TelegramUser):
        location = update.effective_message.location
        user.options['location'] = {
            'longitude': location.longitude,
            'latitude': location.latitude,
            'last_update': timezone.now().strftime('%d-%m-%y %H:%M'),
        }
        user.save()
        update.effective_message.reply_text(_('update_user_location'), reply_markup=keyboards.main_menu(user))
        update.effective_message.delete()


class ContactMessage(BaseMessageHandler):
    FILTERS = Filters.contact

    def callback(self, bot: Bot, update: Update, user: TelegramUser):
        if update.effective_message.contact.user_id != update.effective_message.from_user.id:
            update.effective_message.reply_text(_('dont_send_someone_phone_number'))
            return False
        user.phone = update.effective_message.contact.phone_number
        user.save()
        update.effective_message.reply_text(
            _('saved_user_phone').format(phone=user.phone),
            reply_markup=keyboards.main_menu(user)
        )
        update.effective_message.delete()


def unknown(bot, update):
    user = TelegramUser.get_user(update.effective_message.from_user)
    update.message.reply_text(_('unknown_message'), reply_markup=keyboards.main_menu(user))
    return 'unknown'


unknown_message = MessageHandler(Filters.all, unknown)
