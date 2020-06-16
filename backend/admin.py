from django.contrib import admin
from django.contrib.auth.models import Group
from django.urls import resolve
from django_telegrambot.apps import DjangoTelegramBot
from telegram.ext import JobQueue

from backend import models as back_models
from backend.bot import job_callbacks

admin.site.unregister(Group)


class CustomTabularInline(admin.TabularInline):

    def get_parent_object_from_request(self, request):
        resolved = resolve(request.path_info)
        if resolved.args:
            return self.parent_model.objects.get(pk=resolved.args[0])
        return None


class ServiceInline(CustomTabularInline):
    model = back_models.Service
    fk_name = 'performer'


class CompanyInline(CustomTabularInline):
    model = back_models.Company
    fk_name = 'profile'


class CompanyCategoryInline(CustomTabularInline):
    model = back_models.Company
    fk_name = 'category'

    def get_queryset(self, request):
        queryset = super(CompanyCategoryInline, self).get_queryset(request)
        if hasattr(request.user, 'profile') and not request.user.is_superuser:
            return request.user.profile.companies.all()
        return queryset


class TimeWorkTabular(CustomTabularInline):
    model = back_models.TimeWork
    fk_name = 'performer'


class GradeInline(CustomTabularInline):
    model = back_models.Grade
    fk_name = 'company'


class NewsInline(CustomTabularInline):
    model = back_models.News
    fk_name = 'company'


@admin.register(back_models.TelegramUser)
class TelegramUserAdmin(admin.ModelAdmin):
    pass


@admin.register(back_models.Service)
class ServiceAdmin(admin.ModelAdmin):

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        if hasattr(request.user, 'profile') and not request.user.is_superuser:
            return queryset.filter(performer__in=request.user.profile.companies.all())
        return queryset


@admin.register(back_models.Profile)
class ProfileAdmin(admin.ModelAdmin):
    inlines = [
        CompanyInline
    ]

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        if hasattr(request.user, 'profile') and not request.user.is_superuser:
            return queryset.filter(id=request.user.profile.id)
        return queryset

    def get_fields(self, request, obj=None):
        fields = super(ProfileAdmin, self).get_fields(request, obj)
        if hasattr(request.user, 'profile') and not request.user.is_superuser:
            return ['name', 'description']
        return fields


@admin.register(back_models.Grade)
class GradeAdmin(admin.ModelAdmin):

    def get_queryset(self, request):
        queryset = super().get_queryset(request).prefetch_related('company')
        if hasattr(request.user, 'profile') and not request.user.is_superuser:
            return queryset.filter(company__in=request.user.profile.companies.all())
        return queryset


@admin.register(back_models.Company)
class CompanyAdmin(admin.ModelAdmin):
    inlines = [
        ServiceInline, TimeWorkTabular, NewsInline, GradeInline
    ]

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        if hasattr(request.user, 'profile') and not request.user.is_superuser:
            return request.user.profile.companies.all()
        return queryset

    def get_fields(self, request, obj=None):
        fields = super(CompanyAdmin, self).get_fields(request, obj)
        if hasattr(request.user, 'profile') and not request.user.is_superuser:
            return fields[1:]
        return fields

    def save_model(self, request, obj, form, change):
        if hasattr(request.user, 'profile') and not request.user.is_superuser:
            obj.profile = request.user.profile
        super(CompanyAdmin, self).save_model(request, obj, form, change)

    def save_formset(self, request, form, formset, change):
        instances = formset.save()
        if issubclass(formset.model, back_models.News):
            dp = DjangoTelegramBot.dispatcher
            if not dp.job_queue:
                job_queue = JobQueue(dp.bot)
                job_queue.set_dispatcher(dp)
                dp.job_queue = job_queue
            for instance in instances:
                self.notification(dp.job_queue, instance)

    @staticmethod
    def notification(job: JobQueue, news: back_models.News):
        when = 5 if not news.notification else news.notification
        job.run_once(job_callbacks.notification_user_news, when=when, context=news)


@admin.register(back_models.Category)
class CategoryAdmin(admin.ModelAdmin):
    inlines = [
        CompanyCategoryInline
    ]


@admin.register(back_models.User)
class UserAdmin(admin.ModelAdmin):
    pass
