# Generated by Django 3.0.6 on 2020-06-06 10:27

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('backend', '0004_telegramuser_options'),
    ]

    operations = [
        migrations.AddField(
            model_name='telegramuser',
            name='phone',
            field=models.CharField(blank=True, max_length=30),
        ),
    ]
