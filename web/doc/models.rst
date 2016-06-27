Models
======

.. py:currentmodule:: attpcdaq.daq.models

Models are the database representations of the components of the DAQ system. They store settings and state information
for the system, and have methods for changing the system state and communicating with the ECC server. This is the main
logic of the application.

Data Source
-----------

.. autoclass:: DataSource
   :members:

Configuration IDs
-----------------

.. autoclass:: ConfigId
   :members:

Experiment
----------

.. autoclass:: Experiment
   :members:

Run metadata
------------

.. autoclass:: RunMetadata
   :members:

Exceptions
----------

.. autoexception:: ECCError


