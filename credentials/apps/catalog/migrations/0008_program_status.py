# -*- coding: utf-8 -*-
# Generated by Django 1.11.15 on 2018-08-22 18:45
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('catalog', '0007_auto_20180823_1309'),
    ]

    operations = [
        migrations.AddField(
            model_name='program',
            name='status',
            field=models.CharField(default='active', max_length=24),
        ),
    ]
