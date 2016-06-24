Views
=====

.. py:currentmodule:: attpcdaq.daq.views

The `views` module contains code that renders the pages of the web application.

Page rendering functions
------------------------

.. autofunction:: status
.. autofunction:: choose_config
.. autofunction:: experiment_settings

Refreshing ECC state
--------------------

.. autofunction:: source_get_state
.. autofunction:: refresh_state_all

Changing ECC state
------------------

.. autofunction:: source_change_state
.. autofunction:: source_change_state_all

Manipulating DAQ models
-----------------------

These class-based views are used to create, read, update, and delete data from the database. They generally
render via forms, and return a usable view with the method `as_view`.

.. autoclass:: AddDataSourceView
.. autoclass:: ListDataSourcesView
.. autoclass:: UpdateDataSourceView
.. autoclass:: RemoveDataSourceView
.. autoclass:: AddDataRouterView
.. autoclass:: ListDataRoutersView
.. autoclass:: UpdateDataRouterView
.. autoclass:: RemoveDataRouterView
.. autoclass:: ListRunMetadataView
.. autoclass:: UpdateExperimentView