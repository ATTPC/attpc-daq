Modeling the system in code
===========================

In the Django framework, *models* are used to represent entities. A model has a collection of *fields* associated with
it, and these fields are mapped to columns in the model's representation in the database. The models in the AT-TPC
DAQ app are used to represent components of the DAQ system, including things like ECC servers and data routers. This
page will provide an overview of the different models in the system and how they work together. For more specific
information about each model, refer to their individual pages.

..  currentmodule:: attpcdaq.daq.models

The ECC server (:class:`ECCServer`)
-----------------------------------

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

The data router (:class:`DataRouter`)
-------------------------------------

The :class:`DataRouter` model stores information about data routers in the system. The data router processes are each
associated with one data source, and they record the data stream from that source to a GRAW file. This model simply
stores information about the data router like its IP address, port, and connection type. This information is forwarded
to the data sources when the ECC server configures them.

The data source (:class:`DataSource`)
-------------------------------------

This represents a source of data, like a CoBo or a MuTAnT. This is functionally just a link between an ECC server,
which controls the source, and a data router, which receives data from the source.

Config file sets (:class:`ConfigId`)
------------------------------------

Sets of config files are represented as :class:`ConfigId` objects. These contain fields for each of the three config
files for the three configuration steps. These sets will generally be created automatically by fetching them from the
ECC servers using :meth:`ECCServer.refresh_configs`, but they can also be created manually if necessary.

Run and experiment metadata (:class:`Experiment` and :class:`RunMetadata`)
--------------------------------------------------------------------------

These two models store information about the experiment and the runs it contains. They are used to number the runs and
to store metadata like the experiment name, the duration of each run, and a comment describing the conditions for
each run. More fields could be added to the :class:`RunMetadata` model in the future to store more information.
