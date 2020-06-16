import logging

from django_telegrambot.apps import DjangoTelegramBot
from telegram.ext import JobQueue

from backend.bot.handlers import all_commands, all_messages, all_callback_queries, errors as error_handlers
from backend.bot.handlers.messages import unknown_message

logger = logging.getLogger(__name__)


def init_handler(dispatcher, *list_handlers):
    for handlers in list_handlers:
        for handler in handlers:
            dispatcher.add_handler(handler())


def main():
    logger.info("Loading handlers for telegram bot")
    dp = DjangoTelegramBot.dispatcher
    if not dp.job_queue:
        job_queue = JobQueue(dp.bot)
        job_queue.set_dispatcher(dp)
        dp.job_queue = job_queue
    print(dp.job_queue)
    init_handler(dp, all_commands, all_messages, all_callback_queries)
    dp.add_handler(unknown_message)
    dp.add_error_handler(error_handlers.error)
