Devices in Brian 2
==================

Brian supports generating standalone code for multiple devices. In
this mode, running a Brian script generates source code in a project
tree for the target device/language. This code can then be compiled
and run on the device, and modified if needed. The Brian2GeNN package
provides such a 'device' to run `Brian 2 <https://brian2.readthedocs.io>`_ code
on the `GeNN <http://genn-team.github.io/genn/>`_ (GPU enhanced
Neuronal Networks) backend. GeNN is in itself a code-generation based
framework to generate and execute code for NVIDIA CUDA. Through
Brian2GeNN one can hence generate and run CUDA code on NVIDIA GPUs
based solely in Brian 2 input.

Using the Brian2GeNN interface
==============================

In order to use the Brian2GeNN interface, all three Brian 2, GeNN and
Brian2GeNN need to be fully installed. For GeNN there is also a
dependency on a valid CUDA installation and a CUDA driver, as well as
an NVIDIA graphics adaptor. For installation instructions see XX
(Brian 2), YY (GeNN) and ZZ (Brian2GeNN).

To use the interface one then needs to import the brian2genn interface::

  import brian2genn

The you need to choose the 'genn' device at the
beginning of the Brian 2 script, i.e. after the import statements,
add::

  set_device('genn')

At the encounter of the first ``run`` statement (Brian2GeNN does currently
only support a single ``run`` statement per script), code for GeNN will be
generated, compiled and executed.

The ``set_device`` function can also take additional arguments, e.g. to run
GeNN in its "CPU-only" mode and to get additional debugging output, use::

  set_device('genn', useGPU=False, debug=True)

Not all features of Brian work with Brian2GeNN. The current list of
excluded features is detailed in :doc:`exclusions`.
