from django.contrib import admin

from backend import models as back_models


class ServiceInline(admin.TabularInline):
    model = back_models.Service
    fk_name = 'performer'


class InstitutionInline(admin.TabularInline):
    model = back_models.Institution
    fk_name = 'profile'


class InstitutionCategoryInline(admin.TabularInline):
    model = back_models.Institution
    fk_name = 'category'


class TimeWorkTabular(admin.TabularInline):
    model = back_models.TimeWork
    fk_name = 'performer'


class GradeInline(admin.TabularInline):
    model = back_models.Grade
    fk_name = 'target_user'


@admin.register(back_models.TelegramUser)
class TelegramUserAdmin(admin.ModelAdmin):
    inlines = [
        GradeInline
    ]


@admin.register(back_models.ServiceType)
class ServiceTypeAdmin(admin.ModelAdmin):
    pass


@admin.register(back_models.Service)
class ServiceAdmin(admin.ModelAdmin):
    pass


@admin.register(back_models.Profile)
class ProfileAdmin(admin.ModelAdmin):
    inlines = [
        InstitutionInline
    ]


@admin.register(back_models.Grade)
class GradeAdmin(admin.ModelAdmin):
    pass


@admin.register(back_models.Institution)
class InstitutionAdmin(admin.ModelAdmin):
    inlines = [
        ServiceInline, TimeWorkTabular
    ]


@admin.register(back_models.Category)
class CategoryAdmin(admin.ModelAdmin):
    inlines = [
        InstitutionCategoryInline
    ]


@admin.register(back_models.User)
class UserAdmin(admin.ModelAdmin):
    pass
