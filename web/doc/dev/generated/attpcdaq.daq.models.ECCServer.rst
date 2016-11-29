attpcdaq.daq.models.ECCServer
=============================

.. currentmodule:: attpcdaq.daq.models

.. autoclass:: ECCServer

   .. rubric:: Fields

   .. autosummary::

      ~ECCServer.name
      ~ECCServer.ip_address
      ~ECCServer.port
      ~ECCServer.is_online
      ~ECCServer.is_transitioning
      ~ECCServer.log_path
      ~ECCServer.selected_config
      ~ECCServer.state

   .. rubric:: State constants and attributes

   .. autosummary::

      ~ECCServer.DESCRIBED
      ~ECCServer.IDLE
      ~ECCServer.PREPARED
      ~ECCServer.READY
      ~ECCServer.RUNNING
      ~ECCServer.RESET
      ~ECCServer.STATE_DICT

   .. rubric:: Methods

   .. autosummary::
      :toctree:

      ~ECCServer.change_state
      ~ECCServer.get_data_link_xml_from_clients
      ~ECCServer.refresh_configs
      ~ECCServer.refresh_state
      ~ECCServer._get_soap_client
      ~ECCServer._get_transition
