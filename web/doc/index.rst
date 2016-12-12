AT-TPC DAQ Help
===============

This manual describes how to install, set up, and use the web-based GUI for the AT-TPC's DAQ system. The documentation
is divided into a few different sections. For some background information about the system, see :ref:`overview`.
The :ref:`installation` section describes how to install the system and its dependencies, like Docker. The next
two sections, :ref:`configuration` and :ref:`runlogs`, show how to set up the system for data taking.

The most important section of this manual for experimenters taking shifts is probably :ref:`operations`. It
describes how to configure the CoBos and start and stop runs. It also has instructions on how to record parameters
about the runs, like pressures and voltages.

At the end of the manual is the :ref:`code_docs` section, which contains information about how the system is
implemented. This is probably only of interest to people who want to maintain the system or add new features.

Contents
--------

..  toctree::
    :maxdepth: 2

    overview.rst
    installation.rst
    configuration.rst
    runlogs.rst
    operations.rst
    dev/dev_index.rst


