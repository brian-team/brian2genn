Exclusions in Brian2GeNN
========================

Summed variables
--------------------
Summed variables are currently not supported in GeNN due to the cross-
population nature of this feature. However, a simple form of summed
variable is supported and intrinsic to GeNN. This is the action of
'pre' code in a ``Synapses`` definition onto a pre-synaptic
variable. The allowed interaction is summing onto one pre-synaptic
variable from each ``Synapses`` group.


Linked variables
--------------------
Linked variables create a communication overhead that is problematic in
GeNN. They are therefore at the moment not supported. In principle
support for this feature could be added but in the meantime we suggest
to look into avoiding linked variables by combining groups that are
linked.
For example::

  example


Timed arrays
--------------------
Timed arrays post a problem in the Brian2GeNN interface because they
necessitate communication from teh timed array to the target group at
runtime that would result in host to GPU copies in the final CUDA/C++
code. This could lead to large inefficiences and for the moment we
have therefore decided to not support this feature.


Multiple clocks
--------------------
GeNN is by design operated with a single clock with a fixed time step
across the entire simulation. If you are using multiple clocks and
they are commencurate, please reformulate your script using just the
fastest clock as the standard clock. If your clocks are not
commensurate, and this is essential for your simulation, Brian2GeNN
can unfortunately not be used.

Multiple runs
--------------------
GeNN is designed for single runs and cannot be used for the Brian style
multiple runs. However, if this is of use, code can be run repeatedly
"in multiple runs" that are completely independent. This just needs a
``reset_device`` command issued after the ``run(runtime)`` and
``device.build(...,run=True,...)`` commands. Note, however, that these
multiple runs are completely independent, i.e. for the second run the
code generation pipeline for Brian2GeNN is repeated in its entirety
which may incur a measurable delay.

Multiple networks
--------------------
Multiple networks cannot be supporten in the Brian2GeNN
interface. Please use only the ``magicnetwork``, i.e. refrain from
defining any ``Network`` objects.
