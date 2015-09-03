Devices in Brian 2
=====================

Brian supports generating standalone code for multiple devices. In
this mode, running a Brian script generates source code in a project
tree for the target device/language. This code can then be compiled
and run on the device, and modified if needed. The Brian2GeNN package
provides such a 'device' to run Brian 2 code on the GeNN (GPU enhanced
nNeuronal Networks) backend. GeNN is in itself a code-generation based
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

Then, after ``run(duration)`` in your script, add::

  device.build(directory='output', compile=True, run=True, useGPU='True')

The build function has several arguments to specify the output
directory, whether or not to compile and run the project after
creating it and whether to actually run on a GPU or to use the CPU
mode of GeNN.

Alternatively, one can use the 'simple device' to avoid having to give
the somewhat involved build command. In this case one would set the
command::
  set_device('genn_simple')

And this would automatically trigger a build with ``run=True`` after
each ``run(duration)`` command.

Not all features of brian work with Brian2GeNN. The current list of
excluded features is detailed in :doc:`exclusions`.
