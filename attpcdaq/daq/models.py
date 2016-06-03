from django.db import models


class DataSource(models.Model):
    name = models.CharField(max_length=50)
    ecc_server_url = models.URLField(verbose_name='ECC server URL')
    config = models.CharField(max_length=120, verbose_name='Configuration name')
    state = models.IntegerField(default=0)

    @property
    def state_name(self):
        state_map = {0: 'Idle',
                     1: 'Described',
                     2: 'Prepared',
                     3: 'Configured',
                     4: 'Running'}
        return state_map.get(self.state, 'Error')

    def __str__(self):
        return self.name