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

    ..  note::

        This model stores configuration names using the convention of the ECC server. This means
        that the actual filenames seen by the ECC server will be, for example, ``describe-[name].xcfg``.
        The prefix and file extension are added automatically by the ECC server.

    """

    #: The name of the configuration for the "describe" step
    describe = models.CharField(max_length=120)

    #: The name of the configuration for the "prepare" step
    prepare = models.CharField(max_length=120)

    #: The name of the configuration for the "configure" step
    configure = models.CharField(max_length=120)

    #: The ECC server that this configuration set is associated with
    ecc_server = models.ForeignKey('ECCServer', on_delete=models.CASCADE, null=True, blank=True)

    #: The date and time when this config was fetched from the ECC server. This is used to remove
    #: outdated configs from the database and prevent duplication.
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
    """Represents an individual ECC server which may control one or more data sources.

    This object is responsible for the bulk of the program's work. It is capable of communicating with the ECC
    server process to change the state of a CoBo or MuTAnT, and it also maintains a record of the ECC server's
    current state.

    Data sources are associated with an ECC server through a many-to-one relationship, meaning that one ECC server
    may control many data sources. Alternatively, each data source may have its own ECC server, if that is desired.
    """
    #: A unique name for the ECC server
    name = models.CharField(max_length=50)

    #: The IP address of the ECC server
    ip_address = models.GenericIPAddressField(verbose_name='IP address')

    #: The TCP port that the ECC server listens on. The default value is 8083.
    port = models.PositiveIntegerField(default=8083)

    #: The experiment that this server is associated with.
    experiment = models.ForeignKey('Experiment', on_delete=models.CASCADE)

    #: The configuration file set this ECC server will use
    selected_config = models.ForeignKey(ConfigId, on_delete=models.SET_NULL, null=True, blank=True)

    #: The path to the ECC server process's log file on the computer where the process is running.
    log_path = models.CharField(max_length=500, default='~/Library/Logs/getEccSoapServer.log')

    #: The path to where the config files are stored on the remote computer.
    config_root = models.CharField(max_length=500, default='/Volumes/configs')

    #: Path where config file backups should be stored
    config_backup_root = models.CharField(max_length=500, default='~/config_backups')

    #: A constant representing the "idle" state
    IDLE = 1

    #: A constant representing the "described" state
    DESCRIBED = 2

    #: A constant representing the "prepared" state
    PREPARED = 3

    #: A constant representing the "ready" state
    READY = 4

    #: A constant representing the "running" state
    RUNNING = 5

    #: A constant that is used to tell the system to step backwards by one state
    RESET = -1

    #: A tuple of choices for the ``state`` field
    STATE_CHOICES = ((IDLE, 'Idle'),
                     (DESCRIBED, 'Described'),
                     (PREPARED, 'Prepared'),
                     (READY, 'Ready'),
                     (RUNNING, 'Running'))

    #: A dictionary mapping state constants back to state names
    STATE_DICT = dict(STATE_CHOICES)

    #: The state of the ECC server with respect to the CoBo state machine. This must be one of the choices defined by
    #: the constants attached to this class.
    state = models.IntegerField(default=IDLE, choices=STATE_CHOICES)

    #: Whether the ECC server is currently changing state
    is_transitioning = models.BooleanField(default=False)

    #: Whether the ECC server process is currently available and responding to requests
    is_online = models.BooleanField(default=False)

    class Meta:
        ordering = ('name',)
        unique_together = ('name', 'experiment')

    def __str__(self):
        return self.name

    @property
    def ecc_url(self):
        """Get the URL of the ECC server as a string.
        """
        return 'http://{}:{}/'.format(self.ip_address, self.port)

    def config_file_paths(self):
        """Get the paths to the config files on the remote computer.

        Returns
        -------
        describe_path, prepare_path, configure_path : str
            The full paths to the three config files.
        """
        if self.selected_config is None:
            raise RuntimeError('No config is selected for this ECC server.')

        suffix = 'xcfg'
        filenames = (step + '-' + getattr(self.selected_config, step) + '.' + suffix
                     for step in ('describe', 'prepare', 'configure'))
        paths = (os.path.join(self.config_root, f) for f in filenames)

        return tuple(paths)

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
        """Look up the appropriate SOAP request to change the ECC server from one state to another.

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

        This will update the :attr:`~ECCServer.state` and :attr:`~ECCServer.is_transitioning` fields of the
        :class:`ECCServer`.

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

        If the request is successful, the :attr:`~ECCServer.is_transitioning` field will be set to True, but the
        :attr:`~ECCServer.state` field will *not* be updated automatically. To update this,
        :meth:`~ECCServer.refresh_state` should be called to see if the transition has completed.

        Parameters
        ----------
        target_state : int
            The desired final state. The required transition will be computed using :meth:`~ECCServer._get_transition`.

        Raises
        ------
        RuntimeError
            If the data source does not have a config set.
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
    """Represents the data router associated with one data source.

    Each source of data (a CoBo or a MuTAnT) must be associated with a data router. The data router receives
    the data stream from the source and records it. This model stores information like the IP address, port,
    and type of the data router.
    """
    #: A unique name for the data router
    name = models.CharField(max_length=50)

    #: The IP address of the data router
    ip_address = models.GenericIPAddressField(verbose_name='IP address')

    #: The TCP port where the data router is listening. The default value is 46005.
    port = models.PositiveIntegerField(default=46005)

    #: A constant for the "ICE" protocol
    ICE = 'ICE'

    #: A constant for the "ZBUF" protocol
    ZBUF = 'ZBUF'

    #: A constant for the "TCP" protocol. This is the default for the CoBo.
    TCP = 'TCP'

    #: A constant for the "FDT" protocol. This is the default for the MuTAnT.
    FDT = 'FDT'

    #: A tuple of data router types for the :attr:`~DataRouter.connection_type` field
    DATA_ROUTER_TYPES = ((ICE, 'ICE'),
                         (TCP, 'TCP'),
                         (FDT, 'FDT'),
                         (ZBUF, 'ZBUF'))

    #: The protocol of the data router. This must be one of the constants defined in this class.
    #: The default value is :attr:`~DataRouter.TCP`.
    connection_type = models.CharField(max_length=4, choices=DATA_ROUTER_TYPES, default=TCP)

    #: The experiment that this data router is associated with.
    experiment = models.ForeignKey('Experiment', on_delete=models.CASCADE)

    #: The path to the log file on the computer where the data router is running.
    log_path = models.CharField(max_length=500, default='~/Library/Logs/dataRouter.log')

    #: Whether the data router is online and available
    is_online = models.BooleanField(default=False)

    #: Whether the directory where the data router is running contains any GRAW files.
    staging_directory_is_clean = models.BooleanField(default=True)

    class Meta:
        ordering = ('name',)
        unique_together = ('name', 'experiment')

    def __str__(self):
        return self.name


class DataSource(models.Model):
    """A source of data, probably a CoBo or a MuTAnT.

    This model represents a source of data in the system, like a CoBo or a MuTAnT. A data source is controlled by
    an ECC server, and it sends its data to a data router. Therefore, this is simply a link between an
    :class:`ECCServer` instance and a :class:`DataRouter` instance.
    """

    #: A unique name for the data source. This *must* correspond to an entry in the appropriate config file.
    #: For example, if your config file has an entry for a CoBo with ID 3, this name *must* be
    #: "CoBo[3]". If your config file has an entry for a MuTAnT with ID "master", the corresponding name must be
    #: "Mutant[master]". If this is not correct, the ECC server will return an error during the Configure transition.
    name = models.CharField(max_length=50)

    #: The :class:`ECCServer` that controls this data source. One :class:`ECCServer` may control many data sources.
    ecc_server = models.ForeignKey(ECCServer, on_delete=models.SET_NULL, null=True)

    #: The :class:`DataRouter` that receives the data stream from this source. Each source must have
    #: its own unique :class:`DataRouter`.
    data_router = models.OneToOneField(DataRouter, on_delete=models.SET_NULL, null=True)

    class Meta:
        ordering = ('name',)
        unique_together = ('name', 'ecc_server', 'data_router')

    def __str__(self):
        return self.name

    def get_data_link_xml(self):
        """Get an XML representation of the data link for this source.

        This is used by the ECC server to establish a connection between the CoBo or MuTAnT and the
        data router. The format is as follows:

        .. code-block:: xml

            <DataLink>
                <DataSender id="[DataSource.name]">
                <DataRouter name="[DataSource.data_router_name]"
                            ipAddress="[DataSource.data_router_ip_address]"
                            port="[DataSource.data_router_port]"
                            type="[DataSource.data_router_type]">
            </DataLink>

        This must be wrapped in ``<DataLinkSet>`` tags before sending it to the ECC server.

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

    This model keeps track of run numbers and knows the name of the experiment. It is queried when
    rearranging data files at the end of a run, when the experiment name is used as the name of the directory
    in which to store the files.
    """

    #: The name of the experiment. This must be unique.
    name = models.CharField(max_length=100, unique=True)

    #: Is this the active experiment? Only one experiment may be active at a time.
    is_active = models.BooleanField(default=False)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        """Override of save to enforce only one active experiment at a time."""
        # http://stackoverflow.com/a/1455507/3820658
        if self.is_active:
            try:
                currently_active = Experiment.objects.get(is_active=True)
                if currently_active != self:
                    assert not ECCServer.objects.exclude(state=ECCServer.IDLE).exists(), \
                        "Cannot change experiments with ECCs running"
                    currently_active.is_active = False
                    currently_active.save()
            except Experiment.DoesNotExist:
                pass

        super().save(*args, **kwargs)

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

        The number returned is the run number from :attr:`~Experiment.latest_run` plus 1. Therefore, if a run is
        currently being recorded, this function will return the current run number plus 1.

        If there are no runs, this will return 0.

        Returns
        -------
        int
            The next run number.
        """
        latest_run = self.latest_run
        if latest_run is not None:
            return latest_run.run_number + 1
        else:
            return 0

    def start_run(self):
        """Creates and saves a new :class:`RunMetadata` object with the next run number for the experiment.

        The :attr:`~RunMetadata.start_datetime` field of the created :class:`RunMetadata` instance is set to the
        current date and time.

        Raises
        ------
        RuntimeError
            If there is already a run that has started but not stopped.

        """
        if self.is_running:
            raise RuntimeError('Stop the current run before starting a new one')

        config_names = {ecc.selected_config.configure for ecc in self.eccserver_set.all()}
        config_names_str = ', '.join(config_names)

        RunMetadata.objects.create(
            experiment=self,
            run_number=self.next_run_number,
            start_datetime=datetime.now(),
            config_name=config_names_str,
        )

    def stop_run(self):
        """Stops the current run.

        This sets the :attr:`~RunMetadata.stop_datetime` of the current run to the current date and time,
        effectively ending the run.

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

    Fields can be added to this model to store any type of data we want to record about each run. For instance,
    a title can be added so we know what the run was recording.

    """

    class Meta:
        verbose_name = 'run'

    #: The experiment that this run is a part of
    experiment = models.ForeignKey(Experiment, on_delete=models.CASCADE)

    #: The run number
    run_number = models.PositiveIntegerField()

    #: The date and time when the run started
    start_datetime = models.DateTimeField(null=True, blank=True, verbose_name='start date/time')

    #: The date and time when the run ended
    stop_datetime = models.DateTimeField(null=True, blank=True, verbose_name='stop date/time')

    #: A title or comment describing the run
    title = models.CharField(max_length=200, null=True, blank=True)

    #: The name of the config file set used for this run
    config_name = models.CharField(max_length=100, null=True, blank=True)

    #: Constant for a testing run
    TESTING = 'TEST'

    #: Constant for a production run
    PRODUCTION = 'PROD'

    #: Constant for a beam trigger run
    BEAM = 'BEAM'

    #: Constant for a junk run
    JUNK = 'JUNK'

    #: Constant for a pulser run
    PULSER = 'PULS'

    run_class_choices = (
        (TESTING, 'Testing'),
        (PRODUCTION, 'Production'),
        (BEAM, 'Beam'),
        (JUNK, 'Junk'),
        (PULSER, 'Pulser'),
    )

    #: The type of run this represents. Use one of the constants attached to this class.
    run_class = models.CharField(max_length=4, choices=run_class_choices)

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


class Observable(models.Model):
    """Something that can be measured.

    Observables correspond to columns in a run sheet. Add a new one to add a new field to the run sheet.

    """
    #: The experiment that this observable is associated with.
    experiment = models.ForeignKey(Experiment, on_delete=models.CASCADE)

    #: The name of the observable
    name = models.CharField(max_length=80)

    #: The units that measurements will be recorded in. This will be displayed next to the
    #: input field on the measurement entry form. No unit conversions will be performed.
    units = models.CharField(max_length=40, null=True, blank=True)

    #: A comment to describe how to take a measurement, for example.
    comment = models.CharField(max_length=200, null=True, blank=True)

    #: Constant for an integer measurement
    INTEGER = 'I'

    #: Constant for a floating-point measurement
    FLOAT = 'F'

    #: Constant for a string measurement
    STRING = 'S'

    value_type_choices = (
        (INTEGER, 'Integer'),
        (FLOAT, 'Float'),
        (STRING, 'String'),
    )

    #: The data type of the measurement. Use one of the constants attached to this class.
    value_type = models.CharField(max_length=1, choices=value_type_choices)

    #: The order in which we should display the observables
    order = models.IntegerField(default=1000)  # HACK: use a large default to put new ones on the bottom

    class Meta:
        ordering = ('order', 'pk')

    def __str__(self):
        return self.name


class Measurement(models.Model):
    """A measurement of an Observable.

    Measurements are like instances of Observables. When you fill in the run sheet, a Measurement is created for
    each Observable-related field on the sheet.

    """

    #: The run that this measurement is for
    run_metadata = models.ForeignKey(RunMetadata, on_delete=models.CASCADE)

    #: The Observable that this is a measurement of
    observable = models.ForeignKey(Observable, on_delete=models.CASCADE)

    #: The value as a string
    serialized_value = models.CharField(max_length=100, null=True, blank=True)

    _type_map = {
        Observable.INTEGER: int,
        Observable.FLOAT: float,
        Observable.STRING: str,
    }

    @property
    def python_type(self):
        """The Python data type we expect for this measurement."""
        return self._type_map[self.observable.value_type]

    @property
    def value(self):
        """The value, converted to the expected data type."""
        if self.serialized_value is not None:
            return self.python_type(self.serialized_value)
        else:
            return None

    @value.setter
    def value(self, new_value):
        if isinstance(new_value, self.python_type):
            self.serialized_value = str(new_value)
        elif new_value is None:
            self.serialized_value = None
        else:
            received_type = type(new_value)
            raise ValueError('New value was of type{:s}. Expected {:s}.'.format(
                str(received_type), str(self.python_type)))
