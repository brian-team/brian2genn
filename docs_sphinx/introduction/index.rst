Using Brian2GeNN
================

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

Installing the Brian2GeNN interface
-----------------------------------

In order to use the Brian2GeNN interface, all three Brian 2, GeNN and
Brian2GeNN need to be fully installed. The easiest way to do this is by using
the `conda <https://conda.io/docs/>`_ package provided in the
`brian-team channel <https://anaconda.org/brian-team>`_ on https://anaconda.org.
This will install Brian 2 and its dependencies, and Brian2GeNN with an internal
version of GeNN (you can always switch to using an existing GeNN installation
by setting the `devices.genn.path` preference). Note that this will *not*
install the CUDA toolkit and driver necessary to run simulations on a NVIDIA
graphics card. These will have to be installed manually, e.g. from `NVIDIA's
web site <https://developer.nvidia.com/cuda-downloads>`_ (you can always run
simulations in the "CPU-only" mode, but that of course defeats the main
purpose of Brian2GeNN...). Depending on the installation method, you might
also have to manually set the ``CUDA_PATH`` environment variable (or
alternatively the `devices.genn.cuda_path` preference) to point to
CUDA's installation directory.

To install Brian2GeNN via conda use::

    conda install -c brian-team brian2genn

If you are not using the conda package manager or if there is no conda package
for your architecture, you can always install brian2genn from its source
package on http://pypi.python.org/ ::

    pip install brian2genn

(might require administrator privileges depending on the configuration of your
system; add ``--user`` to force an installation with user privileges only).
Note that in this case, GeNN needs to be installed manually (see its
`installation instructions <http://genn-team.github.io/genn/documentation/html/Installation.html>`_),
and either the ``GENN_PATH`` environment variable of the `devices.genn.path`
preference have to point to its directory. In addition, the CUDA libraries have
to be installed (see above).

.. note::
    The above commands install the necessary packages to run simulations with
    Brian2/GeNN, but most users would install additional packages, e.g.
    `matplotlib <http://matplotlib.org/>`_ for plotting. This can be done with
    the same package management tools mentioned above, e.g. use
    ``conda install matplotlib`` or ``pip install matplotlib``.

Using the Brian2GeNN interface
------------------------------

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
