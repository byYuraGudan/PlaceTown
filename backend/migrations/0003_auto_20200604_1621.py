# Generated by Django 3.0.6 on 2020-06-04 16:21

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('backend', '0002_auto_20200603_1605'),
    ]

    operations = [
        migrations.AddField(
            model_name='service',
            name='description',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='grade',
            name='reviewer_user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='grades', to='backend.TelegramUser'),
        ),
        migrations.AlterField(
            model_name='service',
            name='type',
            field=models.SmallIntegerField(choices=[(0, 'simple_text'), (1, 'alone_order_complete')]),
        ),
        migrations.AlterUniqueTogether(
            name='grade',
            unique_together={('reviewer_user', 'company')},
        ),
        migrations.CreateModel(
            name='Comment',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('text', models.TextField()),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('order', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='comments', to='backend.Order')),
                ('reviewer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='comments', to='backend.TelegramUser')),
            ],
        ),
        migrations.RemoveField(
            model_name='grade',
            name='comment',
        ),
    ]