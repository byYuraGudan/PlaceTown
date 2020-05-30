from django.contrib import admin

from backend import models as back_models


class ServiceInline(admin.TabularInline):
    model = back_models.Service
    fk_name = 'performer'


class CompanyInline(admin.TabularInline):
    model = back_models.Company
    fk_name = 'profile'


class CompanyCategoryInline(admin.TabularInline):
    model = back_models.Company
    fk_name = 'category'


class TimeWorkTabular(admin.TabularInline):
    model = back_models.TimeWork
    fk_name = 'performer'


class GradeInline(admin.TabularInline):
    model = back_models.Grade
    fk_name = 'company'


@admin.register(back_models.TelegramUser)
class TelegramUserAdmin(admin.ModelAdmin):
    pass


@admin.register(back_models.ServiceType)
class ServiceTypeAdmin(admin.ModelAdmin):
    pass


@admin.register(back_models.Service)
class ServiceAdmin(admin.ModelAdmin):
    pass


@admin.register(back_models.Profile)
class ProfileAdmin(admin.ModelAdmin):
    inlines = [
        CompanyInline
    ]


@admin.register(back_models.Grade)
class GradeAdmin(admin.ModelAdmin):
    pass


@admin.register(back_models.Company)
class CompanyAdmin(admin.ModelAdmin):
    inlines = [
        ServiceInline, TimeWorkTabular, GradeInline
    ]


@admin.register(back_models.Category)
class CategoryAdmin(admin.ModelAdmin):
    inlines = [
        CompanyCategoryInline
    ]


@admin.register(back_models.User)
class UserAdmin(admin.ModelAdmin):
    pass
