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

..  rubric:: Views

..  autosummary::
    :toctree: generated/

    status
    choose_config
    experiment_settings
    show_log_page
    EasySetupPage

..  rubric:: Backend functions

..  autosummary::
    :toctree: generated/

    easy_setup


ECC interaction views
---------------------

..  currentmodule:: attpcdaq.daq.views.api

A few of the views in the module :mod:`attpcdaq.daq.views.api` are used to interact with the ECC servers and request
that they perform some action. These views are called when the user clicks a button to request a state change.

..  autosummary::
    :toctree: generated/

    source_change_state
    source_change_state_all

API views
---------

..  currentmodule:: attpcdaq.daq.views.api

The remaining views in the :mod:`attpcdaq.daq.views.api` module provide an interface to the information stored in the
database. These generate pages that allow the user to add, modify, and remove instances of models. There are also views
that return information from the database so the GUI can be updated by AJAX calls.

Unlike other views described above, the API views for manipulating database objects are based on classes instead of
functions. These are all subclasses of generic views provided by Django, so for more information on these views, take
a look at Django's documentation for class-based views.

..  rubric:: Refreshing data

..  autosummary::
    :toctree: generated/

    refresh_state_all

..  rubric:: Working with data sources

..  autosummary::

    AddDataSourceView
    ListDataSourcesView
    UpdateDataSourceView
    RemoveDataSourceView

..  rubric:: Working with data routers

..  autosummary::

    AddDataRouterView
    ListDataRoutersView
    UpdateDataRouterView
    RemoveDataRouterView

..  rubric:: Working with ECC servers

..  autosummary::

    AddECCServerView
    ListECCServersView
    UpdateECCServerView
    RemoveECCServerView

..  rubric:: Working with run metadata

..  autosummary::

    ListRunMetadataView
    UpdateRunMetadataView
    UpdateLatestRunMetadataView

..  rubric:: Working with Observables

..  autosummary::

    AddObservableView
    ListObservablesView
    UpdateObservableView
    RemoveObservableView

..  rubric:: Setting the ordering of observables

..  autosummary::
    :toctree: generated/

    set_observable_ordering


Helper functions
----------------

..  currentmodule:: attpcdaq.daq.views.helpers

These helper functions are called by some of the views to avoid duplicating code. They are located in the module
:mod:`attpcdaq.daq.views.helpers`.

..  autosummary::
    :toctree: generated/

    calculate_overall_state
    get_ecc_server_statuses
    get_data_router_statuses
    get_status
