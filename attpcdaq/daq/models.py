from django.db import models
import xml.etree.ElementTree as ET


class ECCServer(models.Model):
    name = models.CharField(max_length=100, unique=True)
    ip_address = models.GenericIPAddressField(verbose_name='ECC server IP address')
    port = models.PositiveIntegerField(verbose_name='ECC server port', default=8083)

    def __str__(self):
        return self.name

    @property
    def url(self):
        return 'http://{}:{}/'.format(self.ip_address, self.port)


class ConfigId(models.Model):
    describe = models.CharField(max_length=120)
    prepare = models.CharField(max_length=120)
    configure = models.CharField(max_length=120)

    ecc_server = models.ForeignKey(ECCServer, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return '{}/{}/{}'.format(self.describe, self.prepare, self.configure)

    def as_xml(self):
        root = ET.Element('ConfigId')

        for tag, value in zip(('describe', 'prepare', 'configure'), (self.describe, self.prepare, self.configure)):
            node = ET.SubElement(root, 'SubConfigId', attrib={'type': tag})
            node.text = value

        return ET.tostring(root, encoding='unicode')

    @classmethod
    def from_xml(cls, node):
        new_config = cls()

        if not ET.iselement(node):
            node = ET.fromstring(node)

        if node.tag != 'ConfigId':
            raise ValueError('Not a ConfigId node')
        for subnode in node.findall('SubConfigId'):
            config_type = subnode.get('type')
            if config_type == 'describe':
                new_config.describe = subnode.text
            elif config_type == 'prepare':
                new_config.prepare = subnode.text
            elif config_type == 'configure':
                new_config.configure = subnode.text
            else:
                raise ValueError('Unknown or missing config type: {:s}'.format(config_type))

        return new_config


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

    def get_data_link_xml(self):
        dl_set = ET.Element('DataLinkSet')
        dl = ET.SubElement(dl_set, 'DataLink')
        ET.SubElement(dl, 'DataSender', attrib={'id': self.name})
        ET.SubElement(dl, 'DataRouter', attrib={'name': self.data_router.name,
                                                'ipAddress': self.data_router.ip_address,
                                                'port': str(self.data_router.port),
                                                'type': self.data_router.type})
        return ET.tostring(dl_set, encoding='unicode')
