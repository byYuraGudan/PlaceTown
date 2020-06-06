import calendar
import datetime

from django.conf import settings
from django.utils.translation import gettext as _
from telegram import InlineKeyboardButton as InlBtn, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton, \
    ReplyKeyboardRemove

from backend.bot.handlers.callbacks import LanguageCallback, GradeCompanyCallback, FilterCallback
from backend.models import TelegramUser, Company

MAX_INLINE_BUTTON = 60


def build_menu(buttons, cols=2, header_buttons=None, footer_buttons=None):
    buttons = buttons[:MAX_INLINE_BUTTON]
    menu = [buttons[i:i + cols] for i in range(0, len(buttons), cols)]
    if header_buttons:
        menu.insert(0, [header_buttons] if not isinstance(header_buttons, list) else header_buttons)
    if footer_buttons:
        menu.append([footer_buttons] if not isinstance(footer_buttons, list) else footer_buttons)
    return menu


def main_menu(user):
    keyboards = [_('categories')]
    return ReplyKeyboardMarkup(build_menu(keyboards), resize_keyboard=True)


def language(user: TelegramUser):
    buttons = []
    for key, lang in settings.LANGUAGES:
        buttons.append(
            InlBtn(f"{lang} {'✔️' if key == user.lang else ''}", callback_data=LanguageCallback.set_data(lang=f'{key}'))
        )
    return InlineKeyboardMarkup(build_menu(buttons))


def back_btn(user, callback, **extra_data):
    return [[
        InlBtn(user.get_translate('back'), callback_data=callback.set_callback_data(st='back', **extra_data))
    ]]


def site_btn():
    return InlineKeyboardMarkup(build_menu([
        InlBtn(_('site_url'), url=settings.SITE_HOST)
    ]))


def gen_inline_markup(data, callback, title=None, keys=None, cols=2, extra_data=None):
    extra_data = extra_data or {}
    keys = keys or ['id', 'back_data']
    title = title or 'title'
    keyboards = []
    for value in data:
        data_value = {k: v for k, v in value.items() if k in keys}
        callback_data = callback.set_callback_data(**data_value, **extra_data)
        keyboards.append(InlBtn(value[title], callback_data=callback_data))
    return InlineKeyboardMarkup(build_menu(keyboards, cols=cols))


def gen_selected_inline_markup(user, data, callback, back_callback, cols=2, back_data=None, extra_data=None):
    keys = ('id',)
    inline_markup = gen_inline_markup(data, callback, keys=keys, cols=cols)
    footer_keyboards = [
    ]
    inline_markup.inline_keyboard.extend(build_menu(footer_keyboards))
    return inline_markup


def gen_metrics_inline_markup(user, data, callback, back_callback, cols=2, back_data=None, extra_data=None):
    keys = ('id',)
    inline_markup = gen_inline_markup(data, callback, keys=keys, cols=cols)
    footer_keyboards = [
    ]
    inline_markup.inline_keyboard.extend(build_menu(footer_keyboards, cols=1))
    return inline_markup


def generate_calendar(user, callback, year=None, month=None, date_from=None, date_to=None):
    now = datetime.datetime.now()
    if not year:
        year = now.year
    if not month:
        month = now.month
    data_ignore = callback.set_callback_data(st='ignore', year=year, month=month)
    keyboard = [[
        InlBtn(calendar.month_name[month] + " " + str(year), callback_data=data_ignore)
    ]]
    my_calendar = calendar.monthcalendar(year, month)
    for week in my_calendar:
        row = []
        for day in week:
            if not day:
                row.append(InlBtn(" ", callback_data=data_ignore))
            else:
                date = datetime.date(year, month, day)
                text = '*%s' % day if date == date_from.date() or date == date_to.date() else str(day)
                row.append(
                    InlBtn(text, callback_data=callback.set_callback_data(st="day", date=date.strftime('%Y-%m-%d')))
                )
        keyboard.append(row)
    row = []
    row.append(InlBtn("<", callback_data=callback.set_callback_data(st='prev', year=year, month=month - 1)))
    row.append(InlBtn(" ", callback_data=data_ignore))
    row.append(InlBtn(">", callback_data=callback.set_callback_data(st='next', year=year, month=month + 1)))
    keyboard.append(row)

    return InlineKeyboardMarkup(keyboard)


def grade_buttons(company: Company):
    keyboard = [
        InlBtn(f'{i}', callback_data=GradeCompanyCallback.set_data(mark=i, cid=company.id))
        for i in range(1, 6)
    ]
    return InlineKeyboardMarkup(build_menu(keyboard, cols=5))


def filter_markup(user: TelegramUser):
    keyboard = [
        InlBtn(_('by_rating'), callback_data=FilterCallback.set_data(order='rating')),
        InlBtn(_('by_alphabet'), callback_data=FilterCallback.set_data(order='name'))
    ]
    return InlineKeyboardMarkup(build_menu(keyboard, cols=1))


def settings_markup(user: TelegramUser):
    keyboards = [
        KeyboardButton(_('get_location'), request_location=True),
    ]
    if not user.phone:
        keyboards.append(KeyboardButton(_('get_phone'), request_contact=True))
    return ReplyKeyboardMarkup(build_menu(keyboards, cols=1))
