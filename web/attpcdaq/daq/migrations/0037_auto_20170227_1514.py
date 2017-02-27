# -*- coding: utf-8 -*-
# Generated by Django 1.10 on 2017-02-27 15:14
from __future__ import unicode_literals

from django.db import migrations


def get_default_experiment(apps, schema_editor):
    Experiment = apps.get_model('daq', 'Experiment')
    ECCServer = apps.get_model('daq', 'ECCServer')
    DataRouter = apps.get_model('daq', 'DataRouter')

    expt = Experiment.objects.last()
    for ecc in ECCServer.objects.filter(experiment__isnull=True):
        ecc.experiment = expt
        ecc.save()

    for dr in DataRouter.objects.filter(experiment__isnull=True):
        dr.experiment = expt
        dr.save()


class Migration(migrations.Migration):

    dependencies = [
        ('daq', '0036_auto_20170227_1514'),
    ]

    operations = [
        migrations.RunPython(get_default_experiment, reverse_code=migrations.RunPython.noop),
    ]
