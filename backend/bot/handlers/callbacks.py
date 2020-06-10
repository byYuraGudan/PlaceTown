import logging

from django.conf import settings
from django.contrib.auth.models import Group
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext as _, activate
from geopy.distance import geodesic
from telegram import Update, Bot, InlineKeyboardButton as InlBtn, InlineKeyboardMarkup, ParseMode
from telegram.ext import CallbackQueryHandler

from backend.bot import keyboards
from backend.models import TelegramUser, Category, Company, TimeWork, Service, User, Profile, Grade, Order

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
        return {key: int(value) if key.endswith(('id', 'page')) else value for key, value in data}


class LanguageCallback(BaseCallbackQueryHandler):
    LANGUAGES = dict(settings.LANGUAGES)
    PATTERN = 'lang'

    def callback(self, bot: Bot, update: Update, user: TelegramUser, data: dict):
        query = update.callback_query
        user.lang = data.get('lang')
        user.save()
        activate(user.lang)
        query.edit_message_text(_('your_lang').format(self.LANGUAGES.get(data.get('lang'))))
        update.effective_message.reply_text(_('select_you_interested'), reply_markup=keyboards.main_menu(user))


class FilterCallback(BaseCallbackQueryHandler):
    PATTERN = 'filter'

    def callback(self, bot: Bot, update: Update, user: TelegramUser, data: dict):
        query = update.callback_query
        if data.get('st'):
            status = data.pop('st')
            if status == 'open':
                user.options['filters']['open'] = not user.filters['open']
                query.answer(_('open_company') + (' ✅' if user.options['filters']['open'] else ''))
            elif status == 'nearby':
                if not user.location.get('last_update'):
                    query.answer(_('must_update_location'))
                    return False
                location_update = timezone.datetime.strptime(user.location.get('last_update'), '%d-%m-%y %H:%M')
                if divmod((timezone.now().replace(tzinfo=None) - location_update).total_seconds(), 60)[0] > 10:
                    query.answer(_('must_update_location'))
                    return False
                user.options['filters']['nearby'] = not user.filters['nearby']
                query.answer(_('nearby_company') + (' ✅' if user.options['filters']['nearby'] else ''))
            CompaniesCallback.callback(self, bot, update, user, data)
        if data.get('order'):
            order = data.pop('order')
            orders = user.orders
            if order == 'sorting':
                orders['sorting'] = not user.orders.get('sorting', True)
            else:
                orders['by'] = order
            user.options['orders'] = orders
            update.effective_message.edit_reply_markup(reply_markup=keyboards.filter_markup(user))
        if data.get('filter'):
            user.options['filters'][data.get('filter')] = not user.filters.get(data.get('filter'), False)
            update.effective_message.edit_reply_markup(reply_markup=keyboards.filter_markup(user))
        user.save()


class LocationCallback(BaseCallbackQueryHandler):
    PATTERN = 'loc'

    def callback(self, bot: Bot, update: Update, user: TelegramUser, data: dict):
        print(data)


class ProfileCreateCallback(BaseCallbackQueryHandler):
    PATTERN = 'profile'

    def callback(self, bot: Bot, update: Update, user: TelegramUser, data: dict):
        query = update.callback_query
        if not hasattr(user, 'profile'):
            username = user.username or '.'.join(user.full_name.lower().split(' '))
            password = User.objects.make_random_password()
            account = User.objects.create_user(username, password=password, is_staff=True)
            account.groups.add(Group.objects.get(name='ProfileUser'))
            Profile.objects.create(user=user, account=account, name=user.full_name)
            query.edit_message_text(
                _('user_created_info').format(username=username, password=password),
                reply_markup=keyboards.site_btn(),
                parse_mode=ParseMode.HTML,
            )
        else:
            query.edit_message_text(_('profile_exists'), reply_markup=keyboards.site_btn())


class CompanyLocationCallback(BaseCallbackQueryHandler):
    PATTERN = 'location'

    def callback(self, bot: Bot, update: Update, user: TelegramUser, data: dict):
        query = update.callback_query
        company = Company.objects.filter(id=data.get('company_id')).first()
        if not company:
            update.effective_message.reply_text(_('company_doesnt_exists'))
            return
        if not company.latitude and company.longitude:
            update.effective_message.reply_text(_('company_has_not_info_location'))
            return
        update.effective_message.reply_location(company.latitude, company.longitude)
        query.answer(_('location_of_company').format(name=company.name))


class OrderStatusCallback(BaseCallbackQueryHandler):
    PATTERN = 'us-order'

    def callback(self, bot: Bot, update: Update, user: TelegramUser, data: dict):
        query = update.callback_query
        order = Order.objects.filter(id=data.pop('id')).first()
        if not order:
            query.answer(_('no_info_available'))
            return True
        order.status = int(data.pop('status'))
        order.updated = timezone.now()
        order.save()
        user_data, performer_data = {}, {}
        if data.get('st') == 'outgoing':
            user_data = {
                'back_btn': update.effective_message.reply_markup.inline_keyboard[-1:][0],
                'st': 'outgoing'
            }
        elif data.get('st') == 'incoming':
            performer_data = {
                'back_btn': update.effective_message.reply_markup.inline_keyboard[-1:][0],
                'st': 'incoming'
            }
        if data.get('st'):
            update.effective_message.delete()

        self.update_order_user(bot, order, **user_data)
        self.update_performer_order(bot, order, **performer_data)

    @classmethod
    def get_user_order_info(cls, order: Order, user: TelegramUser):
        user.activate()
        return _('created_order_user_info').format(
            status=order.STATUS_DICT.get(order.status),
            company=order.service.performer.name,
            service=order.service.name,
            created=order.created.strftime('%d-%m-%y %H:%M'),
            contact=order.service.performer.contact,
        )

    @classmethod
    def get_user_order_markup(cls, order: Order, user: TelegramUser, back_btn=None, **kwargs):
        if order.status == 3:
            return InlineKeyboardMarkup(keyboards.build_menu([], footer_buttons=back_btn))
        user.activate()
        keyboard = []
        if order.status != 2:
            keyboard.append(InlBtn(_('reject_order'), callback_data=cls.set_data(id=order.id, status=2, **kwargs)))
        return InlineKeyboardMarkup(keyboards.build_menu(keyboard, footer_buttons=back_btn))

    @classmethod
    def get_order_performer_info(cls, order: Order, user: TelegramUser):
        user.activate()
        return _('create_order_performer_info').format(
            status=order.STATUS_DICT.get(order.status),
            service=order.service.name,
            created=order.created.strftime('%d-%m-%y %H:%M'),
            company=order.service.performer.name,
            user_name=order.customer.full_name,
            contact=order.customer.phone,
        )

    @classmethod
    def get_order_performer_markup(cls, order: Order, user: TelegramUser, back_btn=None, **kwargs):
        if order.status in (2, 3):
            return InlineKeyboardMarkup(keyboards.build_menu([], footer_buttons=back_btn))
        user.activate()
        keyboard = []
        if order.status != 1:
            keyboard.append(InlBtn(_('accept_order'), callback_data=cls.set_data(id=order.id, status=1, **kwargs)))
        if order.status != 3:
            keyboard.append(InlBtn(_('done_order'), callback_data=cls.set_data(id=order.id, status=3, **kwargs)))
        keyboard.append(InlBtn(_('reject_order'), callback_data=cls.set_data(id=order.id, status=2, **kwargs)))
        return InlineKeyboardMarkup(keyboards.build_menu(keyboard, footer_buttons=back_btn))

    @classmethod
    def update_order_user(cls, bot: Bot, order: Order, back_btn=None, **kwargs):
        customer, messages = order.get_customer_and_messages
        for message_id in messages:
            try:
                bot.delete_message(customer.id, message_id)
            except:
                log.error(f'Message {message_id} for chat {customer.id} not found')
        text = cls.get_user_order_info(order, customer)
        markup = cls.get_user_order_markup(order, customer, back_btn, **kwargs)
        message = bot.send_message(chat_id=customer.id, text=text, reply_markup=markup)
        order.options['user_messages'] = [message.message_id]
        order.save()

    @classmethod
    def update_performer_order(cls, bot: Bot, order: Order, back_btn=None, **kwargs):
        performer, messages = order.get_performer_and_messages
        for message_id in messages:
            try:
                bot.delete_message(performer.id, message_id)
            except:
                log.error(f'Message {message_id} for chat {performer.id} not found')
        text = cls.get_order_performer_info(order, performer)
        markup = cls.get_order_performer_markup(order, performer, back_btn, **kwargs)
        message = bot.send_message(chat_id=performer.id, text=text, reply_markup=markup)
        order.options['performer_messages'] = [message.message_id]
        order.save()


class CreateOrderCallback(BaseCallbackQueryHandler):
    PATTERN = 'cr-order'

    def callback(self, bot: Bot, update: Update, user: TelegramUser, data: dict):
        query = update.callback_query
        if not user.phone:
            query.answer(_('must_set_user_phone'))
            update.effective_message.reply_text(_('must_set_user_phone'), reply_markup=keyboards.settings_markup(user))
            return False
        service = Service.objects.filter(id=data.pop('id')).first()
        if not service:
            query.answer(_('not_info_about_services_of_company'))
            return False

        if Order.objects.filter(service=service, service__type=1).exclude(status__in=[2, 3]).exists():
            query.answer(_('service_was_early_booking'))
            return False
        markup = update.effective_message.reply_markup
        markup.inline_keyboard = markup.inline_keyboard[1:]
        update.effective_message.edit_reply_markup(reply_markup=markup)
        order = Order.objects.create(customer=user, service=service)
        performer_user = service.performer.profile.user

        user_message = update.effective_message.reply_text(
            OrderStatusCallback.get_user_order_info(order, user),
            reply_markup=OrderStatusCallback.get_user_order_markup(order, user)
        )

        performer_message = bot.send_message(
            performer_user.id,
            OrderStatusCallback.get_order_performer_info(order, performer_user),
            reply_markup=OrderStatusCallback.get_order_performer_markup(order, performer_user)
        )
        order.options.setdefault('user_messages', []).append(user_message.message_id)
        order.options.setdefault('performer_messages', []).append(performer_message.message_id)
        order.save()


class ServiceCompanyCallback(BaseCallbackQueryHandler):
    PATTERN = 'ssid'

    def callback(self, bot: Bot, update: Update, user: TelegramUser, data: dict):
        query = update.callback_query
        service = Service.objects.filter(id=data.pop('id')).first()
        if not service:
            query.answer(_('not_info_about_services_of_company'))
            CompanyDetailCallback.callback(self, bot, update, user, {'id': service.performer.id})
            return False
        if Order.objects.filter(service=service, service__type=1).exclude(status__in=[2, 3]).exists():
            query.answer(_('service_was_early_booking'))
            return False
        buttons = [
            InlBtn(_('create_order'), callback_data=CreateOrderCallback.set_data(id=service.id)),
            InlBtn(_('back'), callback_data=ServicesPaginatorCallback.set_data(page=data.pop('s_pg'), **data))
        ]
        query.edit_message_text(
            _('about_service').format(name=service.name, description=service.description or _('no_info_available')),
            reply_markup=InlineKeyboardMarkup(keyboards.build_menu(buttons, cols=1))
        )


class ServicesPaginatorCallback(BaseCallbackQueryHandler):
    PATTERN = 'services'

    def callback(self, bot: Bot, update: Update, user: TelegramUser, data: dict):
        user.activate()
        query = update.callback_query
        services = Service.objects.filter(performer_id=data['cid']).values('id', 'name').order_by('name')
        excluding_services = Order.objects.filter(service__performer_id=data['cid'], service__type=1) \
            .exclude(status__in=[2, 3]).values('service_id')
        if excluding_services.exists():
            services = services.exclude(id__in=excluding_services)
        if not services:
            query.answer(_('not_info_about_services_of_company'))
            CompanyDetailCallback.callback(self, bot, update, user, {'id': data.get('cid')})
            return False

        from backend.bot import pagination
        paginator = pagination.CallbackPaginator(
            services, ServiceCompanyCallback, self, page=data.get('page', 1),
            page_params={'cid': data['cid']}, data_params={'cid': data['cid'], 's_pg': data.get('page', 1)}
        )
        markup = paginator.inline_markup
        back_btn = [
            InlBtn(
                _('back'),
                callback_data=CompanyDetailCallback.set_data(id=data.get('cid'), page=data.get('ct_pg', 1))),
        ]
        markup.inline_keyboard.append(back_btn)
        query.edit_message_text(_('choose_services_of_company'), reply_markup=markup)


class GradeCompanyCallback(BaseCallbackQueryHandler):
    PATTERN = 'gr-com'

    def callback(self, bot: Bot, update: Update, user: TelegramUser, data: dict):
        query = update.callback_query
        company = Company.objects.filter(id=data.get('cid')).first()

        if not company:
            query.answer(_('not_info_about_company'))
            return False

        if data.get('mark'):
            mark = int(data.get('mark'))
            query.answer(_('your_mark_company_is').format(mark=mark))
            Grade.objects.create(reviewer_user=user, company=company, mark=mark)
            CompanyDetailCallback.callback(self, bot, update, user, {'id': company.id})

        if company.grades.filter(reviewer_user=user).exists():
            query.answer(_('you_are_grade_the_company'))
            return False

        query.edit_message_text(_('grade_the_company'), reply_markup=keyboards.grade_buttons(company))


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
            keyboard.append(InlBtn(_('site_url'), url=company.site))

        if company.longitude and company.latitude:
            callback = CompanyLocationCallback.set_data(company_id=company.id)
            keyboard.append(InlBtn(_('location'), callback_data=callback))

        if not company.grades.filter(reviewer_user=user).exists():
            grade_callback = GradeCompanyCallback.set_data(cid=company.id)
            keyboard.append(InlBtn(_('grade'), callback_data=grade_callback))

        if company.services.exists():
            callback = ServicesPaginatorCallback.set_data(cid=company.id, ct_pg=data.get('ct_pg', 1))
            keyboard.append(InlBtn(_('services'), callback_data=callback))

        from backend.bot.keyboards import build_menu
        back_btn = InlBtn(
            _('back'), callback_data=CompaniesCallback.set_data(
                cid=company.category_id, page=data.get('cp_pg', 1), ct_pg=data.get('ct_pg', 1)
            )
        )
        markup = InlineKeyboardMarkup(build_menu(keyboard, footer_buttons=[back_btn], cols=2))

        text = _('about_company').format(name=company.name,
                                         description=company.description or _('no_info_available'))

        if company.grades.filter(mark__isnull=False).exists():
            grade_mark = company.grades.filter(mark__isnull=False) \
                .aggregate(models.Avg('mark')) \
                .get('mark__avg', 0)
            text += f"\n⭐️: {round(grade_mark, 2)}/5.0"
        if company.address:
            text += f"\n🏢: {company.address}"
        if company.contact:
            text += f"\n📞: {company.contact}"
        if company.email:
            text += f"\n📧: {company.email}"
        text_work_days = "\n{}".format(_('work_schedule'))
        if company.time_works.exists():
            work_week_days = company.time_works \
                .exclude(is_lunch=True) \
                .values('week_day', 'start_time', 'end_time') \
                .order_by('week_day')

            for week in work_week_days:
                text_work_days += "\n{day} {start} - {end}".format(
                    day=TimeWork.WEEK_DAYS_DICT.get(week['week_day']),
                    start=week['start_time'].strftime("%H:%M"),
                    end=week['end_time'].strftime("%H:%M"),
                )
        else:
            text_work_days += _('no_info_available')
        text += f"\n{text_work_days}"

        query.edit_message_text(text, reply_markup=markup, parse_mode=ParseMode.HTML)


class CompaniesCallback(BaseCallbackQueryHandler):
    PATTERN = 'iid'

    def callback(self, bot: Bot, update: Update, user: TelegramUser, data: dict):
        kwargs = {}
        user.activate()
        query = update.callback_query
        from backend.bot import pagination
        companies = Company.objects.filter(category_id=data.get('cid')).values('id', 'name')
        if user.filters['open']:
            time_now = timezone.now()
            open_companies = TimeWork.objects.filter(
                performer__category_id=data.get('cid'),
                week_day=time_now.day - 1,
                start_time__lte=time_now,
                end_time__gte=time_now,
            ).values('performer_id').distinct()
            companies = companies.filter(id__in=open_companies)

        if user.location and user.filters['nearby']:
            companies_dict = {}
            companies_values = Company.objects \
                .filter(longitude__isnull=False, latitude__isnull=False, category_id=data.get('cid')) \
                .values('id', 'longitude', 'latitude')
            companies = companies.filter(id__in=companies_values.values('id').distinct())
            current_location = (user.location['longitude'], user.location['latitude'])
            for company in list(companies_values):
                company_location = (company['longitude'], company['latitude'])
                distance = round(geodesic(current_location, company_location).kilometers * 0.8, 2)
                company['distance'] = distance
                companies_dict[company['id']] = distance
            if companies_values:
                companies_values = sorted(companies_values, reverse=False, key=lambda x: x['distance'])

                sorted_checked = models.Case(
                    *[models.When(pk=pk['id'], then=pos) for pos, pk in enumerate(companies_values)]
                )
                companies = companies.order_by(sorted_checked)
            kwargs['title_pattern'] = lambda x: f"{companies_dict.get(x['id'], '-')} km {x['name']}"

        order = user.orders.get('by')
        if order and not user.filters['nearby']:
            if order == 'mark':
                companies = companies.prefetch_related('grades') \
                    .annotate(mark=models.Avg('grades__mark'))
            if user.orders.get('sorting'):
                order = '-' + order
            companies = companies.order_by(order)

        option_keyboards = [
            [
                InlBtn(
                    _('open_company') + (' ✅' if user.filters.get('open') else ''),
                    callback_data=FilterCallback.set_data(st='open', **data)
                ),
                InlBtn(
                    _('nearby_company') + (' ✅' if user.filters.get('nearby') else ''),
                    callback_data=FilterCallback.set_data(st='nearby', **data)
                ),
            ],
            [
                InlBtn(
                    _('back'),
                    callback_data=CategoriesCallback.set_data(id=data.get('cid'), page=data.get('ct_pg', 1))
                ),
            ]
        ]
        if not companies:
            query.edit_message_text(
                _('not_choose_performer_for_current_category'),
                reply_markup=InlineKeyboardMarkup(option_keyboards)
            )
            return False

        paginator = pagination.CallbackPaginator(
            companies, callback=CompanyDetailCallback, page_callback=self,
            page=data.get('page', 1), callback_data_keys=['id'],
            page_params={'cid': data.get('cid'), 'ct_pg': data.get('ct_pg', 1)},
            data_params={'cp_pg': data.get('page', 1), 'ct_pg': data.get('ct_pg', 1)}, **kwargs
        )
        markup = paginator.inline_markup
        markup.inline_keyboard.extend(option_keyboards)
        query.edit_message_text(_('choose_company'), reply_markup=markup)


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
            callback_data_keys=['cid'], data_params={'ct_pg': data.get('page', 1)}
        )
        query.edit_message_text(_('choose_category'), reply_markup=paginator.inline_markup)


class OutgoingOrderDetailCallback(BaseCallbackQueryHandler):
    PATTERN = 'doid'

    def callback(self, bot: Bot, update: Update, user: TelegramUser, data: dict):
        query = update.callback_query
        order = Order.objects.filter(id=data['id']).first()
        if not order:
            query.answer(_('no_info_available'))
            return False

        back_btn = InlBtn(_('back'), callback_data=OutgoingOrderCallback.set_data(**data))
        query.edit_message_text(
            OrderStatusCallback.get_user_order_info(order, user),
            reply_markup=OrderStatusCallback.get_user_order_markup(order, user, back_btn=back_btn, st='outgoing')
        )


class OutgoingOrderCallback(BaseCallbackQueryHandler):
    PATTERN = 'ooid'

    def callback(self, bot: Bot, update: Update, user: TelegramUser, data: dict):
        query = update.callback_query
        from backend.bot import pagination
        orders = Order.objects.filter(customer=user) \
            .exclude(status__in=user.order_filter_status) \
            .values('id', 'status', 'service__name') \
            .order_by('-updated')

        if not orders:
            query.edit_message_text(_('no_info_available'))
            return False

        paginator = pagination.CallbackPaginator(
            orders, callback=OutgoingOrderDetailCallback, page_callback=self, page=data.get('page', 1),
            callback_data_keys=['id'], data_params={'page': data.get('page', 1)},
            title_pattern=lambda x: f"{Order.STATUS_EMOJI_DICT.get(x['status'])} {x['service__name']}",
        )
        query.edit_message_text(_('choose_order'), reply_markup=paginator.inline_markup)


class IncomingOrderDetailCallback(BaseCallbackQueryHandler):
    PATTERN = 'dioid'

    def callback(self, bot: Bot, update: Update, user: TelegramUser, data: dict):
        query = update.callback_query
        order = Order.objects.filter(id=data['id']).first()
        if not order:
            query.answer(_('no_info_available'))
            return False

        back_btn = InlBtn(_('back'), callback_data=IncomingOrderCallback.set_data(**data))
        query.edit_message_text(
            OrderStatusCallback.get_order_performer_info(order, user),
            reply_markup=OrderStatusCallback.get_order_performer_markup(order, user, back_btn=back_btn, st='incoming')
        )


class IncomingOrderCallback(BaseCallbackQueryHandler):
    PATTERN = 'ioid'

    def callback(self, bot: Bot, update: Update, user: TelegramUser, data: dict):
        query = update.callback_query
        from backend.bot import pagination
        orders = Order.objects.filter(service__performer__profile=user.profile) \
            .exclude(status__in=user.order_filter_status) \
            .values('id', 'status', 'service__name') \
            .order_by('-updated')

        paginator = pagination.CallbackPaginator(
            orders, callback=IncomingOrderDetailCallback, page_callback=self, page=data.get('page', 1),
            callback_data_keys=['id'], data_params={'page': data.get('page', 1)},
            title_pattern=lambda x: f"{Order.STATUS_EMOJI_DICT.get(x['status'])} {x['service__name']}",
        )
        markup = paginator.inline_markup
        markup.inline_keyboard.append([
            InlBtn(_('back'), callback_data=MyProfileCallback.set_data()),
        ])
        query.edit_message_text(_('choose_order'), reply_markup=markup)


class MyProfileCallback(BaseCallbackQueryHandler):
    PATTERN = 'pfid'

    def callback(self, bot: Bot, update: Update, user: TelegramUser, data: dict):
        query = update.callback_query
        query.edit_message_text(_('my_profile_data'), reply_markup=keyboards.profile_markup(user))
