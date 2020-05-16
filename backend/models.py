from django.contrib.auth.models import AbstractUser, UserManager
from django.db import models
from django.utils.translation import activate
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


class Category(MPTTModel, models.Model):
    name = models.CharField(max_length=NAME_LENGTH)
    parent = TreeForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')

    description = models.TextField(blank=True, null=True)
    hidden = models.BooleanField(default=False)


class Grade(models.Model):
    target_user = models.ForeignKey(TelegramUser, on_delete=models.CASCADE, related_name='target')
    reviewer_user = models.ForeignKey(TelegramUser, on_delete=models.CASCADE, related_name='reviewer')

    mark = models.SmallIntegerField()
    comment = models.TextField(blank=True, null=True)
    created = models.DateTimeField(auto_now_add=True)


class Profile(models.Model):
    user = models.ForeignKey(TelegramUser, on_delete=models.CASCADE)

    name = models.CharField(max_length=NAME_LENGTH)
    description = models.TextField(null=True, blank=True)


class ProfileDetail(models.Model):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE)
    category = models.ForeignKey(Category, on_delete=models.PROTECT)

    name = models.CharField(max_length=NAME_LENGTH)
    description = models.TextField(blank=True, null=True)
    contact = models.CharField(max_length=100, blank=True)
    email = models.CharField(max_length=100, blank=True)


class ServiceType(models.Model):
    name = models.CharField(max_length=NAME_LENGTH)
    hidden = models.BooleanField(default=True)


class Service(models.Model):
    performer = models.ForeignKey(ProfileDetail, on_delete=models.CASCADE)
    type = models.ForeignKey(ServiceType, on_delete=models.PROTECT)

    name = models.CharField(max_length=NAME_LENGTH)


class Status(models.Model):
    name = models.CharField(max_length=NAME_LENGTH)
    hidden = models.BooleanField(default=False)


class Order(models.Model):
    status = models.ForeignKey(Status, on_delete=models.PROTECT)
    customer = models.ForeignKey(TelegramUser, on_delete=models.PROTECT)
    service = models.ForeignKey(Service, on_delete=models.PROTECT)

    price = models.DecimalField(max_digits=10, decimal_places=3, default=0, blank=True)

    created = models.DateTimeField(auto_now_add=True, blank=True)
    updated = models.DateTimeField(auto_now_add=True, blank=True)
