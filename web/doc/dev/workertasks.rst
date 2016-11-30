Interfacing with the remote processes
=====================================

The :mod:`attpcdaq.daq.workertasks` module contains a class that uses the Paramiko SSH library to connect to the nodes
running the data router and ECC server in order to, for example, organize files at the end of a run. It can also
check whether these processes are running.

This class should typically be used as a context manager (i.e., with a ``with`` statement). For example, to organize
files, you could try the following:

..  code-block:: python

    with WorkerInterface(data_router_ip_address) as wint:
        wint.organize_files(experiment_name, run_number)

When used in this manner, the SSH session will automatically be opened when entering the ``with`` block and closed
when leaving it.

The WorkerInterface class
-------------------------

..  currentmodule:: attpcdaq.daq.workertasks

..  autoclass:: WorkerInterface

..  rubric:: Methods

..  autosummary::
    :toctree: generated/

    ~WorkerInterface.find_data_router
    ~WorkerInterface.get_graw_list
    ~WorkerInterface.working_dir_is_clean
    ~WorkerInterface.check_ecc_server_status
    ~WorkerInterface.check_data_router_status
    ~WorkerInterface.organize_files
    ~WorkerInterface.tail_file