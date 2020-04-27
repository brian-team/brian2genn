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
``init_sparse_blocksize``can also be configured in this way.

List of preferences
-------------------
.. document_brian_prefs:: devices.genn
