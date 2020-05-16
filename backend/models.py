from django.db import models
from django.utils.translation import activate


class TelegramUser(models.Model):
    id = models.IntegerField(primary_key=True, unique=True, null=False)
    full_name = models.CharField(max_length=100)
    username = models.CharField(max_length=50)
    datetime = models.DateTimeField(auto_now=True)
    state = models.CharField(max_length=100)
    blocked = models.BooleanField(default=False)
    lang = models.CharField(max_length=10, default='uk')

    def __str__(self):
        return '{} - {}'.format(self.id, self.full_name)

    @staticmethod
    def get_user(user):
        defaults = {
            'id': user.id,
            'username': user.username or '',
            'full_name': '{} {}'.format(user.first_name, user.last_name),
            'lang': user.language_code or 'uk',
        }
        user, created = TelegramUser.objects.get_or_create(id=user.id, defaults=defaults)
        activate(user.lang)
        return user
