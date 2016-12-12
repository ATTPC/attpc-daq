..  _runlogs:

Logging information about runs
==============================

In addition to controlling data taking, the DAQ system also allows you to record metadata about each run. This
includes information about when the runs started and stopped along with metadata about the conditions during
the run. This is intended to replace a physical log book with run data sheets. The set of items that are recorded
is customizable, but there are a few fields which are always recorded.

Default run information
-----------------------

The default set of information will be recorded for every run, regardless of configuration. This set of fields
includes the following:

- A sequential run number
- A run class identifying the type of the run. Options include "Testing", "Production", "Beam", "Pulser", and "Junk."
- A title or label for the run
- The date and time when the run started and ended
- The name of the config file(s) used for this run

Adding additional fields
------------------------

In addition to these defaults, any number of custom fields can be added. These fields, known in the DAQ software
as *observables* can be used to record detector parameters like voltages and pressures. These should be set up
at the beginning of an experiment, but they can also be added later.

To set up observables, click "Observables" under "Setup" in the left-hand menu. This will bring you to a list of
the observables that are currently set up in the system. Add a new one by clicking the "Add" button in the
top right corner of the "Observables" panel.

..  tip::

    Observables in this list can be reordered by clicking and dragging the handle on the left-hand side of each row.
    This order will be remembered, and the fields for the observables will be presented in this order when entering
    run information.

An observable has four properties that you can set:

Name
    The name of the measurement. Choose something descriptive, but don't include units. They will be added later.
Value type
    What type of data is this? Options include integer, floating point, and string values.
Units
    The units this will be recorded in. This is just for display, and **no unit conversions will be done** by the
    software.
Comment
    This optional comment will be shown next to the field on the run data sheet for this observable. This could be
    used to make a brief note of how to take a particular measurement, for example.

Fill these fields in and click "Submit" to add a new observable.