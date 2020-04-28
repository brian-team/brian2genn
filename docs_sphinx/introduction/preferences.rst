Brian2GeNN specific preferences
===============================

Connectivity
------------
The preference `devices.genn.connectivity` determines what
connectivity scheme is used within GeNN to represent the connections
between neurons. GeNN supports the use of full connectivity matrices
('DENSE') or a representation where connections are represented with
sparse matrix methods ('SPARSE'). You can set the preference like this::

    from brian2 import *
    import brian2genn
    set_device('genn')

    prefs.devices.genn.connectivity = 'DENSE'


Compiler preferences
--------------------
On Linux and Mac, Brian2GeNN will use the compiler preferences specified for Brian2 
for compiling the executable. This means you should set the
``codegen.cpp.extra_compile_args`` preference, or
``codegen.cpp.extra_compile_args_gcc``

Brian2GeNN also offers a preference to specify additional compiler flags for
CUDA compilation on Linux and Mac with the nvcc compiler:
`devices.genn.cuda_backend.extra_compile_args_nvcc`.

Note that all of the above preferences expect a *Python list* of individual
compiler arguments, i.e. to for example add an argument for the nvcc compiler,
use::

    prefs.devices.genn.cuda_backend.extra_compile_args_nvcc += ['--verbose']

On Windows, Brian2GeNN will try to find the file ``vcvarsall.bat`` to enable
compilation with the MSVC compiler automatically. If this fails, or if you have
multiple versions of MSVC installed and want to select a specific one, you can
set the ``codegen.cpp.msvc_vars_location`` preference.

CUDA preferences
--------------------
The `devices.genn.cuda_backend` preferences contain CUDA-specific preferences.
If you have multiple CUDA devices you can manually select a device like this::

    prefs.devices.genn.cuda_backend.device_select = 'MANUAL'
    prefs.devices.genn.cuda_backend.manual_device = 1

Normally GeNN automatically optimizes the 'block size' used for its CUDA kernels but this 
can also be overriden like::

    prefs.devices.genn.cuda_backend.blocksize_select_method = 'MANUAL'
    prefs.devices.genn.cuda_backend.neuron_blocksize = 64

``pre_neuron_reset_blocksize``, ``pre_synapse_reset_blocksize``, ``synapse_blocksize``, 
``learning_blocksize``, ``synapse_dynamics_blocksize``, ``init_blocksize`` and 
``init_sparse_blocksize`` can also be configured in this way.

List of preferences
-------------------

.. _brian-pref-devices-genn-connectivity:

``devices.genn.connectivity`` = ``'SPARSE'``
    This preference determines which connectivity scheme is to be employed within GeNN. The valid alternatives are 'DENSE' and 'SPARSE'. For 'DENSE' the GeNN dense matrix methods are used for all connectivity matrices. When 'SPARSE' is chosen, the GeNN sparse matrix representations are used.

.. _brian-pref-devices-genn-kernel-timing:

``devices.genn.kernel_timing`` = ``False``
    This preference determines whether GeNN should record kernel runtimes; note that this can affect performance.

.. _brian-pref-devices-genn-path:

``devices.genn.path`` = ``None``
    The path to the GeNN installation (if not set, the version of GeNN in the path will be used instead)

.. _brian-pref-devices-genn-synapse-span-type:

``devices.genn.synapse_span_type`` = ``'POSTSYNAPTIC'``
    This preference determines whether the spanType (parallelization mode) for a synapse population should be set to pre-synapstic or post-synaptic.

.. document_brian_prefs:: devices.genn.cuda_backend
