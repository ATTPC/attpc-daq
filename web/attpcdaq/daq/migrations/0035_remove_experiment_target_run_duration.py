# -*- coding: utf-8 -*-
# Generated by Django 1.10 on 2017-02-27 14:35
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('daq', '0034_remove_experiment_user'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='experiment',
            name='target_run_duration',
        ),
    ]