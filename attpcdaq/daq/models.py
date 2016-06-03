from django.db import models
import xml.etree.ElementTree as ET


class ConfigId(models.Model):
    describe = models.CharField(max_length=120)
    prepare = models.CharField(max_length=120)
    configure = models.CharField(max_length=120)

    def as_xml(self):
        root = ET.Element('ConfigId')

        for tag, value in zip(('describe', 'prepare', 'configure'), (self.describe, self.prepare, self.configure)):
            node = ET.SubElement(root, 'SubConfigId', attrib={'type': tag})
            node.text = value

        return ET.dump(root)


class ECCServer(models.Model):
    name = models.CharField(max_length=100, unique=True)
    ip_address = models.GenericIPAddressField(verbose_name='ECC server IP address')
    port = models.PositiveIntegerField(verbose_name='ECC server port', default=8083)

    available_configs = models.ForeignKey(ConfigId, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return self.name


class DataRouter(models.Model):
    name = models.CharField(max_length=100, unique=True)
    ip_address = models.GenericIPAddressField(verbose_name='Data router IP address')
    port = models.PositiveIntegerField(verbose_name='Data router port')

    ICE = 'ICE'
    ZBUF = 'ZBUF'
    TCP = 'TCP'
    FDT = 'FDT'
    DATA_ROUTER_TYPES = ((ICE, 'ICE'),
                         (TCP, 'TCP'),
                         (FDT, 'FDT'),
                         (ZBUF, 'ZBUF'))
    type = models.CharField(max_length=4, choices=DATA_ROUTER_TYPES, default=TCP)

    def __str__(self):
        return self.name


class DataSource(models.Model):
    name = models.CharField(max_length=50)
    ecc_server = models.OneToOneField(ECCServer, on_delete=models.SET_NULL, null=True, blank=True)
    data_router = models.OneToOneField(DataRouter, on_delete=models.SET_NULL, null=True, blank=True)
    config = models.ForeignKey(ConfigId, on_delete=models.SET_NULL, null=True, blank=True)

    IDLE = 0
    DESCRIBED = 1
    PREPARED = 2
    CONFIGURED = 3
    RUNNING = 4
    STATE_CHOICES = ((IDLE, 'Idle'),
                     (DESCRIBED, 'Described'),
                     (PREPARED, 'Prepared'),
                     (CONFIGURED, 'Configured'),
                     (RUNNING, 'Running'))
    state = models.IntegerField(default=IDLE, choices=STATE_CHOICES)

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
