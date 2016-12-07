..  _models:

Modeling the system in code
===========================

In the Django framework, *models* are used to represent entities. A model has a collection of *fields* associated with
it, and these fields are mapped to columns in the model's representation in the database. The models in the AT-TPC
DAQ app are used to represent components of the DAQ system, including things like ECC servers and data routers. This
page will provide an overview of the different models in the system and how they work together. For more specific
information about each model, refer to their individual pages.

..  currentmodule:: attpcdaq.daq.models

DAQ system components
---------------------

The GET DAQ system is modeled using three classes: the :class:`ECCServer`, the :class:`DataRouter`, and the
:class:`DataSource`.

The ECC server
~~~~~~~~~~~~~~

The :class:`ECCServer` model is responsible for all communication with the GET ECC server processes. There should
be one instance of this model for each ECC server in the system. The :class:`ECCServer` has fields that store the
IP address and port of the ECC server, and it also keeps track of which configuration file set to use, what the
state of the ECC server is with respect to the CoBo state machine, and whether the ECC server is online and reachable.

In addition to storing basic information about the ECC servers, this model also has methods that allow it to communicate
with the ECC server it represents. The :meth:`~ECCServer.refresh_configs` method fetches the list of available
configuration file sets from the ECC server and stores it in the database. The :meth:`~ECCServer.refresh_state` method
fetches the current CoBo state machine state from the ECC server and updates the :attr:`~ECCServer.state` field
accordingly. Finally, the method :meth:`~ECCServer.change_state` will tell the ECC server to transition its data
sources to a different state. This last method is used to configure, start, and stop the CoBos during data taking.

Communication with the ECC server is done using the SOAP protocol. This is performed by a third-party library which is
wrapped by the :class:`EccClient` class in this module. The interface to the ECC server is defined by the file
``web/attpcdaq/daq/ecc.wsdl``, which was copied from the source of the GET ECC server into this package. If the
interface is updated in a future version of the ECC server, this file should be replaced.

The data router
~~~~~~~~~~~~~~~

The :class:`DataRouter` model stores information about data routers in the system. The data router processes are each
associated with one data source, and they record the data stream from that source to a GRAW file. This model simply
stores information about the data router like its IP address, port, and connection type. This information is forwarded
to the data sources when the ECC server configures them.

The data source
~~~~~~~~~~~~~~~

This represents a source of data, like a CoBo or a MuTAnT. This is functionally just a link between an ECC server,
which controls the source, and a data router, which receives data from the source.

.. rubric:: DAQ component models

..  autosummary::
    :toctree: generated/

    ECCServer
    DataRouter
    DataSource


Config file sets
----------------

Sets of config files are represented as :class:`ConfigId` objects. These contain fields for each of the three config
files for the three configuration steps. These sets will generally be created automatically by fetching them from the
ECC servers using :meth:`ECCServer.refresh_configs`, but they can also be created manually if necessary.

..  rubric:: Config file models

..  autosummary::
    :toctree: generated/

    ConfigId


Run and experiment metadata
---------------------------

The :class:`Experiment` and :class:`RunMetadata` models store information about the experiment and the runs it contains.
They are used to number the runs and to store metadata like the experiment name, the duration of each run, and a
comment describing the conditions for each run.

The :class:`Observable` and :class:`Measurement` classes are used to store measurements of experimental parameters
like voltages, pressures, and scalers. An :class:`Observable` defines a quantity that can be measured, and each one
adds a new field that can be filled in on the Run Info sheet. When a user fills in values for an :class:`Observable`,
a corresponding :class:`Measurement` object is created to store that value. This design was chosen so that the user
can add new observables at any time without reloading the code or altering the database structure. This would not
be possible if we just defined a new field on the :class:`RunMetadata` object for each observable.

..  rubric:: Metadata models

..  autosummary::
    :toctree: generated/

    Experiment
    RunMetadata
    Observable
    Measurement