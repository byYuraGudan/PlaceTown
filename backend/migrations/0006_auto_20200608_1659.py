# Generated by Django 3.0.6 on 2020-06-08 13:59

import django.contrib.postgres.fields.jsonb
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('backend', '0005_telegramuser_phone'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='options',
            field=django.contrib.postgres.fields.jsonb.JSONField(default=dict),
        ),
        migrations.AlterField(
            model_name='order',
            name='status',
            field=models.SmallIntegerField(choices=[(0, 'waiting'), (1, 'accepted'), (2, 'rejected'), (3, 'done')], default=0),
        ),
    ]