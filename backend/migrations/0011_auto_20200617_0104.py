# Generated by Django 3.0.6 on 2020-06-17 01:04

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('backend', '0010_auto_20200616_2111'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='news',
            name='notification',
        ),
        migrations.AddField(
            model_name='news',
            name='notification_users',
            field=models.BooleanField(blank=True, default=False),
        ),
    ]