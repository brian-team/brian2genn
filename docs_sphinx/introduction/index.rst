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
Brian2GeNN need to be fully installed.
To install GeNN and Brian 2, refer to their respective documentation:

* `Brian 2 installation instructions <https://brian2.readthedocs.io/en/stable/introduction/install.html>`_
* `GeNN installation instructions <http://genn-team.github.io/genn/documentation/4/html/d8/d99/Installation.html>`_

Note that you will have to also install the CUDA toolkit and driver necessary
to run simulations on a NVIDIA graphics card. These will have to be installed
manually, e.g. from `NVIDIA's web site <https://developer.nvidia.com/cuda-downloads>`_
(you can always run simulations in the "CPU-only" mode, but that of course
defeats the main purpose of Brian2GeNN...). Depending on the installation
method, you might also have to manually set the ``CUDA_PATH`` environment
variable (or alternatively the `devices.genn.cuda_backend.cuda_path` preference) to point to
CUDA's installation directory.

To install brian2genn, use ``pip``::

    pip install brian2genn

(might require administrator privileges depending on the configuration of your
system; add ``--user`` to force an installation with user privileges only).

As detailed in the `GeNN installation instructions <http://genn-team.github.io/genn/documentation/4/html/d8/d99/Installation.html>`_),
you also need to ensure that GeNN's bin directory is added to your path.
Alternatively, you can set the `devices.genn.path` preference to your GeNN directory to achieve the same effect.

.. note::
    We no longer provide conda packages for Brian2GeNN. Conda packages for
    previous versions of Brian2GeNN have been tagged with the ``archive`` label
    and are still available in the ``brian-team`` channel.

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

  set_device('genn', use_GPU=False, debug=True)

Not all features of Brian work with Brian2GeNN. The current list of
excluded features is detailed in :doc:`exclusions`.
