from django.utils import timezone
from telegram.ext import Job

from django.utils.translation import gettext as _
from telegram import Bot, InlineKeyboardButton as InlBtn, InlineKeyboardMarkup, ParseMode


def notification_user_news(bot: Bot, job: Job):
    from backend.bot.handlers.callbacks import CompanyDetailCallback

    news = job.context
    print('Start Notification news {}!!'.format(news.title))

    if not news.notification_users:
        job.schedule_removal()
        return

    company = news.company
    for watch in company.watches.all():
        watch.telegram_user.activate()
        reply_markup = InlineKeyboardMarkup([[
            InlBtn(_('company'), callback_data=CompanyDetailCallback.set_data(id=news.company.id))
        ]])
        text = _('notification_news').format(
            company=company.name,
            title=news.title,
            description=news.description,
            time_news=timezone.now().strftime('%d-%m-%y %H:%M')
        )
        bot.send_message(
            chat_id=watch.telegram_user.id, text=text, reply_markup=reply_markup, parse_mode=ParseMode.HTML
        )
    job.schedule_removal()
