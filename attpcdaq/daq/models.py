from django.db import models


class DataSource(models.Model):
    name = models.CharField(max_length=50)
    ecc_server_url = models.URLField(verbose_name='ECC server URL')
    config = models.CharField(max_length=120, verbose_name='Configuration name')
    state = models.IntegerField()