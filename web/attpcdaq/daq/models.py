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

import logging
logger = logging.getLogger(__name__)


class ECCError(Exception):
    """Indicates that something went wrong during communication with the ECC server."""
    pass


class EccClient(object):
    def __init__(self, ecc_url):
        """A wrapper around the Zeep library's SOAP client.

        This exists to help prevent future problems if the Client class from zeep changes. That
        library is under heavy development, so it might break things in the future.

        The methods of this class are implemented by overriding `__getattr__` to pass along calls to
        the `self.service` attribute. The available methods are those defined by the SOAP protocol,
        and they are listed below.

        Methods
        -------
        GetConfigIDs()
            Get a list of the config files known to the ECC server.
        GetState()
            Fetch the current state of the ECC state machine.
        Describe(config_xml, datasource_xml)
            Perform the Describe transition.
        Prepare(config_xml, datasource_xml)
            Perform the Prepare transition.
        Configure(config_xml, datasource_xml)
            Perform the Configure transition.
        Start()
            Start acquisition.
        Stop()
            Stop acquisition.
        Breakup()
            Performs the inverse of Configure.
        Undo()
            Performs the inverse of Prepare or Describe.

        Parameters
        ----------
        ecc_url : str
            The full URL of the ECC server (i.e. "http://{address}:{port}").

        """
        wsdl_url = os.path.join(settings.BASE_DIR, 'attpcdaq', 'daq', 'ecc.wsdl')
        client = SoapClient(wsdl_url)  # Loads the service definition from ecc.wsdl
        self.service = client.create_service('{urn:ecc}ecc', ecc_url)  # This overrides the default URL from the file

        # This is a list of valid operations which is used in __getattr__ below.
        self.operations = ['GetState',
                           'Describe',
                           'Prepare',
                           'Configure',
                           'Start',
                           'Stop',
                           'Undo',
                           'Breakup',
                           'GetConfigIDs']

    def __getattr__(self, item):
        if item in self.operations:
            return getattr(self.service, item)

        else:
            raise AttributeError('EccClient has no attribute {}'.format(item))


class ConfigId(models.Model):
    """Represents a configuration file set as seen by the ECC servers.

    This will generally be retrieved from the ECC servers using a SOAP call. If this is the case, an
    object can be constructed from the XML representation using the class method ``from_xml``.

    It is important to note that this is just a representation of the config files which is used
    for communicating with the ECC server. No actual configuration is done by this program.

    Attributes
    ----------
    describe, prepare, configure : models.CharField
        The names of the files used in each respective step. The actual filenames, as seen by
        the ECC server, will be, for example, ``describe-[name].xcfg``. The prefix and file extension
        are added automatically by the ECC server.
    data_source : models.ForeignKey
        The ECC server which this config set is associated with. This may be null.
    last_fetched : models.DateTimeField
        The date and time when this config was fetched from the ECC server. This is used to remove
        outdated configs from the database.

    """
    describe = models.CharField(max_length=120)
    prepare = models.CharField(max_length=120)
    configure = models.CharField(max_length=120)

    ecc_server = models.ForeignKey('ECCServer', on_delete=models.CASCADE, null=True, blank=True)

    last_fetched = models.DateTimeField(default=datetime.now)

    class Meta:
        ordering = ('describe', 'prepare', 'configure')

    def __str__(self):
        return '{}/{}/{}'.format(self.describe, self.prepare, self.configure)

    def as_xml(self):
        """Get an XML representation of the object.

        This is useful for sending to the ECC server. The format is as follows:

        .. code-block:: xml

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
            committed to the database, so one should call ``new_config.save()`` if that is desired.

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


class ECCServer(models.Model):
    name = models.CharField(max_length=50, unique=True)
    ip_address = models.GenericIPAddressField(verbose_name='IP address')
    port = models.PositiveIntegerField(default=8083)

    # Config file information
    selected_config = models.ForeignKey(ConfigId, on_delete=models.SET_NULL, null=True, blank=True)

    log_path = models.CharField(max_length=500, default='~/Library/Logs/getEccSoapServer.log')

    # Status information
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

    is_online = models.BooleanField(default=False)

    class Meta:
        ordering = ('name',)

    def __str__(self):
        return self.name

    @property
    def ecc_url(self):
        """Get the URL of the ECC server as a string.
        """
        return 'http://{}:{}/'.format(self.ip_address, self.port)

    def _get_soap_client(self):
        """Creates a SOAP client for communicating with the ECC server.

        The client loads the WSDL file, which describes the SOAP services, from the local disk. The
        target URL of the client is then set to the ECC server's address.

        Returns
        -------
        EccClient
            The configured SOAP client.

        """
        return EccClient(self.ecc_url)

    @classmethod
    def _get_transition(cls, client, current_state, target_state):
        """Look up the appropriate SOAP request to change the data source from one state to another.

        Given the ``current_state`` and the ``target_state``, this will either return the correct callable to
        make the transition, or it will raise an exception.

        Parameters
        ----------
        client : EccClient
            The SOAP client. One of its methods will be returned.
        current_state : int
            The current state of the ECC state machine.
        target_state : int
            The desired final state of the ECC state machine.

        Returns
        -------
        function
            The function corresponding to the requested transition. This can then be called with the
            appropriate arguments to change the ECC server's state.

        Raises
        ------
        ValueError
            If the requested states differ by more than one transition, or if no transition is needed.

        See Also
        --------
        DataSource.state
        DataSource.STATE_DICT

        """
        if target_state == current_state:
            raise ValueError('No transition needed.')

        transitions = {
            (cls.IDLE, cls.DESCRIBED): client.Describe,
            (cls.DESCRIBED, cls.IDLE): client.Undo,

            (cls.DESCRIBED, cls.PREPARED): client.Prepare,
            (cls.PREPARED, cls.DESCRIBED): client.Undo,

            (cls.PREPARED, cls.READY): client.Configure,
            (cls.READY, cls.PREPARED): client.Breakup,

            (cls.READY, cls.RUNNING): client.Start,
            (cls.RUNNING, cls.READY): client.Stop,
        }

        try:
            trans = transitions[(current_state, target_state)]
        except KeyError:
            raise ValueError('Can only transition one step at a time.') from None

        return trans

    def get_data_link_xml_from_clients(self):
        """Get an XML representation of the data link for this source.

        This is used by the ECC server to establish a connection between the CoBo and the
        data router. The format is as follows:

        .. code-block:: xml

            <DataLinkSet>
                <DataLink>
                    <DataSender id="[DataSource.name]">
                    <DataRouter name="[DataSource.data_router_name]"
                                ipAddress="[DataSource.data_router_ip_address]"
                                port="[DataSource.data_router_port]"
                                type="[DataSource.data_router_type]">
                </DataLink>
            </DataLinkSet>

        Returns
        -------
        str
            The XML data.

        """
        datalink_set = ET.Element('DataLinkSet')
        for source in self.datasource_set.all():
            source_node = source.get_data_link_xml()
            datalink_set.append(source_node)

        return ET.tostring(datalink_set, encoding='unicode')

    def refresh_configs(self):
        """Fetches the list of configs from the ECC server and updates the database.

        If new configs are present on the ECC server, they will be added to the database. If configs are present
        in the database but are no longer known to the ECC server, they will be deleted.

        The old configs are deleted based on their ``last_fetched`` field. Therefore, this field will be updated for
        each existing config set that is still present on the ECC server when this function is called.

        """
        client = self._get_soap_client()
        result = client.GetConfigIDs()
        fetch_time = datetime.now()

        config_list_xml = ET.fromstring(result.Text)
        configs = [ConfigId.from_xml(s) for s in config_list_xml.findall('ConfigId')]
        for config in configs:
            ConfigId.objects.update_or_create(describe=config.describe,
                                              prepare=config.prepare,
                                              configure=config.configure,
                                              ecc_server=self,
                                              defaults={'last_fetched': fetch_time})

        self.configid_set.filter(last_fetched__lt=fetch_time).delete()

    def refresh_state(self):
        """Gets the current state of the data source from the ECC server and updates the database.

        This will update the ``state`` and ``is_transitioning`` fields of the ``DataSource``.

        Raises
        ------
        ECCError
            If the return code from the ECC server is nonzero.
        """
        client = self._get_soap_client()
        result = client.GetState()

        if int(result.ErrorCode) != 0:
            raise ECCError(result.ErrorMessage)

        self.state = int(result.State)
        self.is_transitioning = int(result.Transition) != 0
        self.save()

    def change_state(self, target_state):
        """Tells the ECC server to transition the data source to a new state.

        If the request is successful, the ``is_transitioning`` field will be set to True, but the ``state`` field will
        *not* be updated automatically. To update this, `DataSource.refresh_state` should be called to see if the
        transition has completed.

        Parameters
        ----------
        target_state : int
            The desired final state. The required transition will be computed using `DataSource._get_transition`.

        Raises
        ------
        RuntimeError
            If the data source does not have a config set.

        See Also
        --------
        DataSource._get_transition

        """

        # Get transition arguments
        try:
            config_xml = self.selected_config.as_xml()
        except AttributeError as err:
            raise RuntimeError("Data source has no config associated with it.") from err

        datalink_xml = self.get_data_link_xml_from_clients()

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


class DataRouter(models.Model):
    name = models.CharField(max_length=50, unique=True)
    ip_address = models.GenericIPAddressField(verbose_name='IP address')
    port = models.PositiveIntegerField(default=46005)

    ICE = 'ICE'
    ZBUF = 'ZBUF'
    TCP = 'TCP'
    FDT = 'FDT'
    DATA_ROUTER_TYPES = ((ICE, 'ICE'),
                         (TCP, 'TCP'),
                         (FDT, 'FDT'),
                         (ZBUF, 'ZBUF'))
    connection_type = models.CharField(max_length=4, choices=DATA_ROUTER_TYPES, default=TCP)

    log_path = models.CharField(max_length=500, default='~/Library/Logs/dataRouter.log')

    is_online = models.BooleanField(default=False)
    staging_directory_is_clean = models.BooleanField(default=True)

    class Meta:
        ordering = ('name',)

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
    ecc_ip_address : models.GenericIPAddressField
        The IP address of the ECC server.
    ecc_port : models.PositiveIntegerField
        The TCP port that the ECC server listens on.
    data_router_ip_address : models.GenericIPAddressField
        The IP address of the data router. This is where the data will be recorded.
    data_router_port : models.PositiveIntegerField
        The TCP port that the dataRouter process listens on.
    data_router_type : models.CharField
        The type of data stream expected by the data router. This is shown in the output of the data router
        when it first starts, although it is also configurable with a command-line option. The type
        specified must be one of the choices defined in this class.
    selected_config : models.ForeignKey
        The configuration file set this source will use.
    state : models.IntegerField
        The state of the data source, as known by the ECC server. This must be one of the choices defined by
        the constants attached to this class.
    is_transitioning : models.BooleanField
        Whether the data source is currently changing state.
    IDLE, DESCRIBED, PREPARED, READY, RUNNING : int
        Constants representing valid states.
    RESET : int
        A constant to be used in the reset transition. This is not a real state machine state, but is used
        to compute which state should be requested.
    STATE_DICT : dict
        A dictionary for retrieving display names for the above states.
    ICE, ZBUF, TCP, FDT : str
        These are the choices for the data router type.
    daq_state : Models.IntegerField
        The state of the remote DAQ processes. This can indicate if the ECC server and data router are
        alive, and whether the data router's working directory is clean.

    """
    name = models.CharField(max_length=50, unique=True)
    ecc_server = models.ForeignKey(ECCServer, on_delete=models.SET_NULL, null=True)
    data_router = models.OneToOneField(DataRouter, on_delete=models.SET_NULL, null=True)

    class Meta:
        ordering = ('name',)

    def __str__(self):
        return self.name

    def get_data_link_xml(self):
        """Get an XML representation of the data link for this source.

        This is used by the ECC server to establish a connection between the CoBo and the
        data router. The format is as follows:

        .. code-block:: xml

            <DataLink>
                <DataSender id="[DataSource.name]">
                <DataRouter name="[DataSource.data_router_name]"
                            ipAddress="[DataSource.data_router_ip_address]"
                            port="[DataSource.data_router_port]"
                            type="[DataSource.data_router_type]">
            </DataLink>

        This must be wrapped in ``<DataLinkSet>'' tags before sending it to the ECC server.

        Returns
        -------
        xml.etree.ElementTree.Element
            The XML data for this source.

        """
        dl = ET.Element('DataLink')
        ET.SubElement(dl, 'DataSender', attrib={'id': self.name})
        ET.SubElement(dl, 'DataRouter', attrib={'name': self.data_router.name,
                                                'ipAddress': self.data_router.ip_address,
                                                'port': str(self.data_router.port),
                                                'type': self.data_router.connection_type})
        return dl


class Experiment(models.Model):
    """Represents an experiment and the settings relevant to one.

    This class is also responsible for keeping track of run numbers.

    Attributes
    ----------
    user : models.OneToOneField
        The user associated with this experiment.
    name : models.CharField
        The name of the experiment. This must be unique.
    target_run_duration : models.PositiveIntegerField
        The expected duration of a run, in seconds.

    """
    user = models.OneToOneField(User)
    name = models.CharField(max_length=100, unique=True)
    target_run_duration = models.PositiveIntegerField(default=3600)

    def __str__(self):
        return self.name

    @property
    def latest_run(self):
        """Get the most recent run in the experiment.

        This will return the current run if a run is ongoing, or the most recent run if the DAQ is stopped.

        Returns
        -------
        RunMetadata or None
            The most recent or current run. If there are no runs for this experiment, None will be returned instead.

        """
        try:
            return self.runmetadata_set.latest('start_datetime')
        except RunMetadata.DoesNotExist:
            return None

    @property
    def is_running(self):
        """Whether a run is currently being recorded.

        Returns
        -------
        bool
            True if the latest run has started but not stopped. False otherwise (including if there are no runs).

        """
        latest_run = self.latest_run
        if latest_run is not None:
            return latest_run.stop_datetime is None
        else:
            return False

    @property
    def next_run_number(self):
        """Get the number that the next run should have.

        The number returned is the run number from `latest_run` plus 1. Therefore, if a run is currently being
        recorded, this function will return the current run number plus 1.

        If there are no runs, this will return 0.

        Returns
        -------
        int
            The next run number.

        See Also
        --------
        DataSource.latest_run

        """
        latest_run = self.latest_run
        if latest_run is not None:
            return latest_run.run_number + 1
        else:
            return 0

    def start_run(self):
        """Creates and saves a new RunMetadata object with the next run number for the experiment.

        The `start_datetime` field of the created RunMetadata instance is set to the current date and time.

        Raises
        ------
        RuntimeError
            If there is already a run that has started but not stopped.

        """
        if self.is_running:
            raise RuntimeError('Stop the current run before starting a new one')

        new_run = RunMetadata(experiment=self,
                              run_number=self.next_run_number,
                              start_datetime=datetime.now())
        new_run.save()

    def stop_run(self):
        """Sets the `stop_datetime` of the current run to the current date and time, effectively ending the run.

        Raises
        ------
        RuntimeError
            If there is no current run.

        """
        if not self.is_running:
            raise RuntimeError('Not running')

        current_run = self.latest_run
        current_run.stop_datetime = datetime.now()
        current_run.save()


class RunMetadata(models.Model):
    """Represents the metadata describing a data run.

    Attributes
    ----------
    experiment : models.ForeignKey
        The experiment this run is for
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
    title = models.CharField(max_length=200, null=True, blank=True)

    def __str__(self):
        return "{} run {}".format(self.experiment.name, self.run_number)

    @property
    def duration(self):
        """Get the duration of the run.

        If the run has not ended, the difference is taken with respect to the current time.

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
        """Get the duration as a string.

        Returns
        -------
        str
            The duration of the current run. The format is HH:MM:SS.

        """
        dur = self.duration
        h, rem = divmod(dur.seconds, 3600)
        m, s = divmod(rem, 60)
        return '{:02d}:{:02d}:{:02d}'.format(h, m, s)
