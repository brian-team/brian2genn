Brian2GeNN specific preferences
===============================

Connectivity
------------
The preference ``devices.genn.connectivity`` determines what
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
Brian2GeNN will use the compiler preferences specified for Brian2 (both for the
C++ compiler call, as well as for NVIDIA's nvcc compiler). This means you should
set the ``codegen.cpp.extra_compile_args`` preference, or set
``codegen.cpp.extra_compile_args_gcc`` and
``codegen.cpp.extra_compile_args_msvc`` to set preferences specifically for
compilation under Linux/OS-X and Windows, respectively.
