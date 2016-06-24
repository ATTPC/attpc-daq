"""AT-TPC DAQ Models

This module defines the internal representation of the DAQ used by this control program.
Each subclass of Model is an object that will be stored in the database, and the Field
subclasses attached as attributes will be the columns in the database table.

"""

from django.db import models
from django.contrib.auth.models import User
from django.conf import settings
import xml.etree.ElementTree as ET
from zeep.client import Client as SoapClient
import os
from datetime import datetime


class ECCError(Exception):
    pass


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

    data_source = models.ForeignKey('DataSource', on_delete=models.CASCADE, null=True, blank=True)

    last_fetched = models.DateTimeField(default=datetime.now)

    @property
    def name(self):
        return str(self)

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
    ecc_ip_address = models.GenericIPAddressField(verbose_name='ECC server IP address')
    ecc_port = models.PositiveIntegerField(verbose_name='ECC server port', default=8083)
    data_router = models.OneToOneField(DataRouter, on_delete=models.SET_NULL, null=True, blank=True)
    selected_config = models.ForeignKey(ConfigId, on_delete=models.SET_NULL, null=True, blank=True)

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
    RESET = -1
    state = models.IntegerField(default=IDLE, choices=STATE_CHOICES)
    is_transitioning = models.BooleanField(default=False)

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

    @property
    def ecc_url(self):
        """Get the URL of the ECC server as a string.
        """
        return 'http://{}:{}/'.format(self.ecc_ip_address, self.ecc_port)

    def _get_soap_client(self):
        wsdl_url = os.path.join(settings.BASE_DIR, 'attpcdaq', 'daq', 'ecc.wsdl')
        client = SoapClient(wsdl_url)
        client.set_address('ecc', 'ecc', self.ecc_url)
        return client

    @classmethod
    def _get_transition(cls, client, current_state, target_state):
        if target_state == current_state:
            raise ValueError('No transition needed.')

        transitions = {
            (cls.IDLE, cls.DESCRIBED): client.service.Describe,
            (cls.DESCRIBED, cls.IDLE): client.service.Undo,

            (cls.DESCRIBED, cls.PREPARED): client.service.Prepare,
            (cls.PREPARED, cls.DESCRIBED): client.service.Undo,

            (cls.PREPARED, cls.READY): client.service.Configure,
            (cls.READY, cls.PREPARED): client.service.Breakup,

            (cls.READY, cls.RUNNING): client.service.Start,
            (cls.RUNNING, cls.READY): client.service.Stop,
        }

        try:
            trans = transitions[(current_state, target_state)]
        except KeyError:
            raise ValueError('Can only transition one step at a time.')

        return trans

    def refresh_configs(self):
        client = self._get_soap_client()
        result = client.service.GetConfigIDs()
        fetch_time = datetime.now()

        config_list_xml = ET.fromstring(result.Text)
        configs = [ConfigId.from_xml(s) for s in config_list_xml.findall('ConfigId')]
        for config in configs:
            ConfigId.objects.update_or_create(describe=config.describe,
                                              prepare=config.prepare,
                                              configure=config.configure,
                                              data_source=self,
                                              defaults={'last_fetched': fetch_time})

        self.configid_set.filter(last_fetched__lt=fetch_time).delete()

    def refresh_state(self):
        client = self._get_soap_client()
        result = client.service.GetState()

        if int(result.ErrorCode) != 0:
            raise ECCError(result.ErrorMessage)

        self.state = int(result.State)
        self.is_transitioning = int(result.Transition) != 0
        self.save()

    def change_state(self, target_state):
        # Get transition arguments
        try:
            config_xml = self.selected_config.as_xml()
        except AttributeError:
            raise RuntimeError("Data source has no config associated with it.")

        try:
            datalink_xml = self.get_data_link_xml()
        except AttributeError:
            raise RuntimeError("Data source has no data router associated with it.")

        client = self._get_soap_client()

        # Get the function corresponding to the requested transition
        transition = self._get_transition(client, self.state, target_state)

        # Finally, perform the transition
        res = transition(config_xml, datalink_xml)

        if int(res.ErrorCode) != 0:
            self.is_transitioning = False
            raise ECCError(res.ErrorMessage)
        else:
            self.is_transitioning = True


class Experiment(models.Model):
    user = models.OneToOneField(User)
    name = models.CharField(max_length=100, unique=True)
    target_run_duration = models.PositiveIntegerField(default=3600)

    @property
    def latest_run(self):
        try:
            return self.runmetadata_set.latest('start_datetime')
        except RunMetadata.DoesNotExist:
            return None

    @property
    def is_running(self):
        latest_run = self.latest_run
        if latest_run is not None:
            return latest_run.stop_datetime is None
        else:
            return False

    @property
    def next_run_number(self):
        latest_run = self.latest_run
        if latest_run is not None:
            return latest_run.run_number + 1
        else:
            return 0

    def start_run(self):
        if self.is_running:
            raise RuntimeError('Stop the current run before starting a new one')

        new_run = RunMetadata(experiment=self,
                              run_number=self.next_run_number,
                              start_datetime=datetime.now())
        new_run.save()

    def stop_run(self):
        if not self.is_running:
            raise RuntimeError('Not running')

        current_run = self.latest_run
        current_run.stop_datetime = datetime.now()
        current_run.save()


class RunMetadata(models.Model):
    """Represents the metadata describing a data run.

    Attributes
    ----------
    run_number : models.PositiveIntegerField
        The run number
    start_datetime : models.DateTimeField
        The date and time when the run started.
    stop_datetime : models.DateTimeField
        The date and time when the run ended.

    """

    class Meta:
        verbose_name = 'run'

    experiment = models.ForeignKey(Experiment, on_delete=models.CASCADE)
    run_number = models.PositiveIntegerField()
    start_datetime = models.DateTimeField(null=True, blank=True)
    stop_datetime = models.DateTimeField(null=True, blank=True)

    @property
    def duration(self):
        """Get the duration of the run.

        Returns
        -------
        datetime.timedelta
            Object representing the duration of the run.
        """
        if self.stop_datetime is not None:
            return self.stop_datetime - self.start_datetime
        else:
            return datetime.now() - self.start_datetime

    @property
    def duration_string(self):
        dur = self.duration
        h, rem = divmod(dur.seconds, 3600)
        m, s = divmod(rem, 60)
        return '{:02d}:{:02d}:{:02d}'.format(h, m, s)
