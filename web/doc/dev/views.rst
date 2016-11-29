Interacting with the system
===========================

Interaction with the Django web app occurs through *views*, which are just functions and classes that Django calls
when certain URLs are requested. Views are used to render the pages of the web app, and they are also how the user
tells the system to "do something" like configure a CoBo or refresh the state of an ECC server.

Views are mapped to URLs automatically by Django. This mapping is set up in the module :mod:`attpcdaq.daq.urls`.

Some views render pages that accept information from the user. These generally use a Django form class to process
the data.

Since the views serve a number of different purposes, they are organized into a few separate modules in the package
:mod:`attpcdaq.daq.views`.

Page rendering views
--------------------

..  currentmodule:: attpcdaq.daq.views.pages

These views, located in the module :mod:`attpcdaq.daq.views.pages`, are used to render the pages of the web app.
This includes functions like :func:`status`, which renders the main status page, and others like :func:`show_log_page`,
which contacts a remote computer, fetches the end of a log file, and renders a page showing it.

..  autosummary::
    :toctree: generated/

    status
    choose_config
    experiment_settings
    remote_status
    show_log_page


Refreshing ECC state
--------------------

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
.. autoclass:: ListRunMetadataView

