import re

from telegram.ext import BaseFilter
from django.utils.translation import gettext as _

from backend.models import TelegramUser


class RegexFilter(BaseFilter):

    def __init__(self, pattern, key):
        self.pattern = pattern
        self.key = key
        self.name = 'Filters.RegexFilter({}{})'.format(self.pattern, key)

    def filter(self, message):
        user = TelegramUser.get_user(message.from_user)
        if message.text:
            pattern = re.compile('{}{}'.format(self.pattern, _(self.key)))
            match = pattern.search(message.text)
            if match:
                return {'matches': [match]}
            return {}
