from django.conf import settings
from django.contrib.auth.models import AbstractUser, UserManager
from django.contrib.gis.db.models import PointField
from django.contrib.postgres.fields import JSONField
from django.db import models
from django.utils.translation import activate, gettext
from django.utils.translation import gettext_lazy as _
from mptt.models import MPTTModel, TreeForeignKey


NAME_LENGTH = 200


class User(AbstractUser):

    objects = UserManager()


class TelegramUser(models.Model):
    id = models.IntegerField(primary_key=True, unique=True, null=False)
    full_name = models.CharField(max_length=100)
    username = models.CharField(max_length=50)
    datetime = models.DateTimeField(auto_now=True)
    state = models.CharField(max_length=100)
    blocked = models.BooleanField(default=False)
    lang = models.CharField(max_length=10, default='uk')
    phone = models.CharField(max_length=30, blank=True)
    options = JSONField(default=dict)

    def __str__(self):
        return f'{self.full_name} - {self.id}'

    @staticmethod
    def get_user(user):
        defaults = {
            'id': user.id,
            'username': user.username or '',
            'full_name': '{} {}'.format(user.first_name or '', user.last_name or ''),
            'lang': user.language_code if user.language_code in dict(settings.LANGUAGES).keys()
            else settings.LANGUAGE_CODE,
        }
        user, created = TelegramUser.objects.get_or_create(id=user.id, defaults=defaults)
        activate(user.lang)
        return user

    def get_text(self, text):
        activate(self.lang)
        return gettext(text)

    def activate(self):
        activate(self.lang)

    @property
    def filters(self):
        return self.options.setdefault(
            'filters', {'open': False, 'nearby': False, 'show_done': False, 'show_rejected': True}
        )

    @property
    def orders(self):
        return self.options.setdefault('orders', {'by': 'name', 'sorting': True})

    @property
    def location(self):
        return self.options.get('location', {})

    @property
    def order_filter_status(self):
        status = []
        if not self.filters.get('show_done'):
            status.append(3)
        if not self.filters.get('show_rejected'):
            status.append(2)
        return status

    class Meta:
        verbose_name = _('telegram_user')
        verbose_name_plural = _('telegram_users')


class Category(MPTTModel, models.Model):
    name = models.CharField(max_length=NAME_LENGTH)
    parent = TreeForeignKey(
        'self', on_delete=models.CASCADE, null=True, blank=True, related_name='children', editable=False
    )

    description = models.TextField(blank=True, null=True)
    hidden = models.BooleanField(default=False)

    def __str__(self):
        return f'{self.name} - {self.id}'

    class Meta:
        verbose_name = _('_category')
        verbose_name_plural = _('_categories')


class Profile(models.Model):
    user = models.OneToOneField(TelegramUser, related_name='profile', on_delete=models.CASCADE)
    account = models.OneToOneField(User, related_name='profile', on_delete=models.PROTECT)

    name = models.CharField(max_length=NAME_LENGTH)
    description = models.TextField(null=True, blank=True)

    def __str__(self):
        return f'{self.name} - {self.id}'

    class Meta:
        verbose_name = _('_profile')
        verbose_name_plural = _('_profiles')


class Company(models.Model):
    profile = models.ForeignKey(Profile, related_name='companies', on_delete=models.CASCADE)
    category = models.ForeignKey(Category, related_name='companies', on_delete=models.PROTECT)

    name = models.CharField(max_length=NAME_LENGTH)
    description = models.TextField(blank=True, null=True)
    address = models.CharField(max_length=255, blank=True)
    contact = models.CharField(max_length=100, blank=True)
    email = models.CharField(max_length=100, blank=True)
    site = models.CharField(max_length=255, blank=True)

    point = PointField(blank=True, null=True, editable=False)
    longitude = models.FloatField(null=True, blank=True, default=None)
    latitude = models.FloatField(null=True, blank=True, default=None)

    def __str__(self):
        return f'{self.name} - {self.id}'

    class Meta:
        verbose_name = _('_company')
        verbose_name_plural = _('_companies')


class TimeWork(models.Model):
    WEEK_DAYS = [
        (0, _('Monday')),
        (1, _('Tuesday')),
        (2, _('Wednesday')),
        (3, _('Thursday')),
        (4, _('Friday')),
        (5, _('Saturday')),
        (6, _('Sunday')),
    ]
    WEEK_DAYS_DICT = dict(WEEK_DAYS)
    performer = models.ForeignKey(Company, related_name='time_works', on_delete=models.CASCADE)
    start_time = models.TimeField()
    end_time = models.TimeField()
    week_day = models.SmallIntegerField(choices=WEEK_DAYS)
    is_lunch = models.BooleanField(default=False)

    def __str__(self):
        return f'{self.WEEK_DAYS_DICT.get(self.week_day)}, {self.start_time} - {self.end_time}'

    class Meta:
        verbose_name = _('_time_work')
        verbose_name_plural = _('_time_works')
        unique_together = ('performer', 'week_day', 'is_lunch')


class WatchCompanyTelegramUser(models.Model):
    telegram_user = models.ForeignKey(TelegramUser, related_name='watches', on_delete=models.CASCADE)
    company = models.ForeignKey(Company, related_name='watches', on_delete=models.CASCADE)
    watch = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('telegram_user', 'company')


class Service(models.Model):
    SERVICE_TYPE = [
        (0, _('simple_text')),
        (1, _('booking'))
    ]
    performer = models.ForeignKey(Company, related_name='services', on_delete=models.CASCADE)
    type = models.SmallIntegerField(choices=SERVICE_TYPE)

    name = models.CharField(max_length=NAME_LENGTH)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return f'{self.name}'

    class Meta:
        verbose_name = _('_service')
        verbose_name_plural = _('_services')


class News(models.Model):
    company = models.ForeignKey(Company, related_name='news', on_delete=models.CASCADE)

    title = models.CharField(max_length=254, null=False)
    description = models.TextField(blank=False, null=False)
    notification_users = models.BooleanField(blank=True, default=False)
    date_from = models.DateField(blank=True, null=True)
    date_to = models.DateField(blank=True, null=True)

    created = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('_news')
        verbose_name_plural = _('_more_news')


class Order(models.Model):
    STATUS = [
        (0, _('waiting')),
        (1, _('accepted')),
        (2, _('rejected')),
        (3, _('done')),
    ]
    STATUS_DICT = dict(STATUS)
    STATUS_EMOJI_DICT = {
        0: '🟡',  # waiting
        1: '🟢',  # accepted
        2: '🔴',  # rejected
        3: '✅',  # done
    }
    status = models.SmallIntegerField(choices=STATUS, default=0)
    customer = models.ForeignKey(TelegramUser, on_delete=models.PROTECT)
    service = models.ForeignKey(Service, on_delete=models.PROTECT)

    options = JSONField(default=dict, null=True)

    price = models.DecimalField(max_digits=10, decimal_places=3, default=0, blank=True)

    created = models.DateTimeField(auto_now_add=True, blank=True)
    updated = models.DateTimeField(auto_now_add=True, blank=True)

    @property
    def get_customer_and_messages(self):
        return self.customer, self.options.setdefault('user_messages', [])

    @property
    def get_performer_and_messages(self):
        return self.service.performer.profile.user, self.options.setdefault('performer_messages', [])

    class Meta:
        verbose_name = _('_order')
        verbose_name_plural = _('_orders')


class Grade(models.Model):
    reviewer_user = models.ForeignKey(TelegramUser, on_delete=models.CASCADE, related_name='grades')
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='grades')

    mark = models.SmallIntegerField()
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('_grade')
        verbose_name_plural = _('_grades')
        unique_together = ('reviewer_user', 'company',)

    def __str__(self):
        return f'{self.company.name} - {self.mark}'


class Comment(models.Model):
    reviewer = models.ForeignKey(TelegramUser, on_delete=models.CASCADE, related_name='comments')
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='comments')

    text = models.TextField()
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('_order')
        verbose_name_plural = _('_orders')
