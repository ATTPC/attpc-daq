"""AT-TPC DAQ Models

This module defines the internal representation of the DAQ used by this control program.
Each subclass of Model is an object that will be stored in the database, and the Field
subclasses attached as attributes will be the columns in the database table.

"""

from django.db import models
import xml.etree.ElementTree as ET


class ECCServer(models.Model):
    """An ECC server.

    Attributes
    ----------
    name : models.CharField
        A unique name to identify the ECC server.
    ip_address : models.GenericIPAddressField
        The IP address of the ECC server.
    port : models.PositiveIntegerField
        The TCP port the ECC server listens on.

    """
    name = models.CharField(max_length=100, unique=True)
    ip_address = models.GenericIPAddressField(verbose_name='ECC server IP address')
    port = models.PositiveIntegerField(verbose_name='ECC server port', default=8083)

    def __str__(self):
        return self.name

    @property
    def url(self):
        """Get the URL of the ECC server as a string.
        """
        return 'http://{}:{}/'.format(self.ip_address, self.port)


class ConfigId(models.Model):
    """Represents a configuration file set as seen by the ECC servers.

    This will generally be retrieved from the ECC servers using a SOAP call. If this is the case, an
    object can be constructed from the XML representation using the class method `from_xml`.

    Attributes
    ----------
    describe, prepare, configure : models.CharField
        The names of the files used in each respective step. The actual filenames, as seen by
        the ECC server, will be, for example, `describe-[name].xcfg`. The prefix and file extension
        are added automatically by the ECC server.
    ecc_server : models.ForeignKey
        The ECC server which this config set is associated with. This may be null.

    """
    describe = models.CharField(max_length=120)
    prepare = models.CharField(max_length=120)
    configure = models.CharField(max_length=120)

    ecc_server = models.ForeignKey(ECCServer, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return '{}/{}/{}'.format(self.describe, self.prepare, self.configure)

    def as_xml(self):
        """Get an XML representation of the object.

        This is useful for sending to the ECC server. The format is as follows:

            <ConfigId>
                <SubConfigId type="describe">[self.describe]</SubConfigId>
                <SubConfigId type="prepare">[self.prepare]</SubConfigId>
                <SubConfigId type="configure">[self.configure]</SubConfigId>
            </ConfigId>

        Returns
        -------
        str
            The XML representation.

        """
        root = ET.Element('ConfigId')

        for tag, value in zip(('describe', 'prepare', 'configure'), (self.describe, self.prepare, self.configure)):
            node = ET.SubElement(root, 'SubConfigId', attrib={'type': tag})
            node.text = value

        return ET.tostring(root, encoding='unicode')

    @classmethod
    def from_xml(cls, node):
        """Construct a ConfigId object from the given XML representation.

        Parameters
        ----------
        node : xml.etree.ElementTree.Element or str
            The XML representation of the object, probably from the ECC server. If it's a string,
            it will be automatically converted to the appropriate XML node object.

        Returns
        -------
        new_config : ConfigId
            A ConfigId object constructed from the representation. Note that this object is **not** automatically
            committed to the database, so one should call `new_config.save()` if that is desired.

        """
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
    """A data router, for receiving data from the CoBos.

    Attributes
    ----------
    name : models.CharField
        A unique name for the data router.
    ip_address : models.GenericIPAddressField
        The IP address of the data router.
    port : models.PositiveIntegerField
        The TCP port the data router listens on.
    type : models.CharField
        The type of connection the data router accepts. This may be one of ICE, ZBUF, TCP, or FDT. The value should
        be set using one of the corresponding attributes on this class.
    ICE, ZBUF, TCP, FDT : str
        Constants representing the available connection types.

    """
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
    """A source of data, probably a CoBo.

    This is the main object in the program. It represents a data source (CoBo) by knowing information about its
    controlling ECC server and corresponding data router and configuration files. It also maintains a record
    of the current state of the ECC state machine, which tells us what the CoBo is doing.

    Attributes
    ----------
    name : models.CharField
        A unique name for the data source. For a CoBo, this *must* correspond to an entry in the appropriate
        config file. For example, if your config file has an entry for a CoBo with ID 3, this name *must* be
        "CoBo[3]". If this is not correct, the ECC server will return an error during the Configure transition.
    ecc_server : models.OneToOneField
        The ECC server controlling this data source.
    data_router : models.OneToOneField
        The data router receiving data from this source.
    config : models.ForeignKey
        The configuration file set this source will use.
    state : models.IntegerField
        The state of the data source, as known by the ECC server. This must be one of the choices defined by
        the constants attached to this class.
    IDLE, DESCRIBED, PREPARED, READY, RUNNING : int
        Constants representing valid states.
    STATE_DICT : dict
        A dictionary for retrieving display names for the above states.

    """
    name = models.CharField(max_length=50, unique=True)
    ecc_server = models.OneToOneField(ECCServer, on_delete=models.SET_NULL, null=True, blank=True)
    data_router = models.OneToOneField(DataRouter, on_delete=models.SET_NULL, null=True, blank=True)
    config = models.ForeignKey(ConfigId, on_delete=models.SET_NULL, null=True, blank=True)

    IDLE = 1
    DESCRIBED = 2
    PREPARED = 3
    READY = 4
    RUNNING = 5
    STATE_CHOICES = ((IDLE, 'Idle'),
                     (DESCRIBED, 'Described'),
                     (PREPARED, 'Prepared'),
                     (READY, 'Ready'),
                     (RUNNING, 'Running'))
    STATE_DICT = dict(STATE_CHOICES)
    state = models.IntegerField(default=IDLE, choices=STATE_CHOICES)

    def __str__(self):
        return self.name

    def get_data_link_xml(self):
        """Get an XML representation of the data link for this source.

        This is used by the ECC server to establish a connection between the CoBo and the
        data router. The format is as follows:

            <DataLinkSet>
                <DataLink>
                    <DataSender id="[DataSource.name]">
                    <DataRouter name="[DataRouter.name]"
                                ipAddress="[DataRouter.ip_address]"
                                port="[DataRouter.port]"
                                type="[DataRouter.type]">
                </DataLink>
            </DataLinkSet>

        Returns
        -------
        str
            The XML data.

        """
        dl_set = ET.Element('DataLinkSet')
        dl = ET.SubElement(dl_set, 'DataLink')
        ET.SubElement(dl, 'DataSender', attrib={'id': self.name})
        ET.SubElement(dl, 'DataRouter', attrib={'name': self.data_router.name,
                                                'ipAddress': self.data_router.ip_address,
                                                'port': str(self.data_router.port),
                                                'type': self.data_router.type})
        return ET.tostring(dl_set, encoding='unicode')
