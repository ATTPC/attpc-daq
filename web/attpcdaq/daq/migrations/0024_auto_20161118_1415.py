# -*- coding: utf-8 -*-
# Generated by Django 1.10 on 2016-11-18 14:15
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('daq', '0023_auto_20161117_2208'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='datasource',
            name='daq_state',
        ),
        migrations.AddField(
            model_name='datarouter',
            name='is_online',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='datarouter',
            name='staging_directory_is_clean',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='eccserver',
            name='is_online',
            field=models.BooleanField(default=False),
        ),
    ]
