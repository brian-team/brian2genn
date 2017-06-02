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
Brian2GeNN will use the compiler preferences specified for Brian2 for the
C++ compiler call. This means you should set the
``codegen.cpp.extra_compile_args`` preference, or set
``codegen.cpp.extra_compile_args_gcc`` and
``codegen.cpp.extra_compile_args_msvc`` to set preferences specifically for
compilation under Linux/OS-X and Windows, respectively.

Brian2GeNN also offers a preference to specify additional compiler flags for the
CUDA compilation with the nvcc compiler: `devices.genn.extra_compile_args_nvcc`.

Note that all of the above preferences expect a *Python list* of individual
compiler arguments, i.e. to for example add an argument for the nvcc compiler,
use::

    prefs.devices.genn.extra_compile_args_nvcc += ['--verbose']

On Windows, Brian2GeNN will try to find the file ``vcvarsall.bat`` to enable
compilation with the MSVC compiler automatically. If this fails, or if you have
multiple versions of MSVC installed and want to select a specific one, you can
set the ``codegen.cpp.msvc_vars_location`` preference.

List of preferences
-------------------
.. document_brian_prefs:: devices.genn
