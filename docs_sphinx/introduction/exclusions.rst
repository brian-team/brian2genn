Unsupported features in Brian2GeNN
==================================

.. highlight:: python
   :linenothreshold: 5

Restrictions on summed variables
--------------------------------
Summed variables are supported starting with version 1.4. There are a number of
restrictions, however. Most importantly:

* the equations of a `Synapses` object can only use a single summed variable
* a summed variable cannot be combined with another action on a post-synaptic variable
  in the ``on_pre`` statement (e.g. ``g_exc_post += w_exc``).


Linked variables
----------------
Linked variables create a communication overhead that is problematic in
GeNN. They are therefore at the moment not supported. In principle
support for this feature could be added but in the meantime we suggest
to look into avoiding linked variables by combining groups that are
linked.
For example

.. code-block:: python
  :emphasize-lines: 8,15,20

  from brian2 import *
  import brian2genn
  set_device('genn_simple')

  # Common deterministic input
  N = 25
  tau_input = 5*ms
  input = NeuronGroup(N, 'dx/dt = -x / tau_input + sin(0.1*t/ tau_input) : 1')

  # The noisy neurons receiving the same input
  tau = 10*ms
  sigma = .015
  eqs_neurons = '''
  dx/dt = (0.9 + .5 * I - x) / tau + sigma * (2 / tau)**.5 * xi : 1
  I : 1 (linked)
  '''
  neurons = NeuronGroup(N, model=eqs_neurons, threshold='x > 1',
                        reset='x = 0', refractory=5*ms)
  neurons.x = 'rand()'
  neurons.I = linked_var(input, 'x') # input.x is continuously fed into neurons.I
  spikes = SpikeMonitor(neurons)

  run(500*ms)example

could be replaced by

.. code-block:: python
  :emphasize-lines: 12

  from brian2 import *
  import brian2genn
  set_device('genn_simple')

  N = 25
  tau_input = 5*ms

  # Noisy neurons receiving the same deterministic input
  tau = 10*ms
  sigma = .015
  eqs_neurons = '''
  dI/dt= -I / tau_input + sin(0.1*t/ tau_input) : 1')
  dx/dt = (0.9 + .5 * I - x) / tau + sigma * (2 / tau)**.5 * xi : 1
  '''
  neurons = NeuronGroup(N, model=eqs_neurons, threshold='x > 1',
                        reset='x = 0', refractory=5*ms)
  neurons.x = 'rand()'
  spikes = SpikeMonitor(neurons)

  run(500*ms)example

In this second solution the variable I is calculated multiple times
within the 'noisy neurons', which in a sense is an unnecessary
computational overhead. However, in the massively parallel GPU
accelerators this is not necessarily a problem. Note that this method
only works where the common input is deterministic. If the input had
been::

  input = NeuronGroup(1, 'dx/dt = -x / tau_input + (2 /tau_input)**.5 * xi : 1')

i.e. contains a random element, then moving the common input into the
'noisy neuron' population would make it individual, independent noisy
inputs with likely quite different results.

Custom events
-------------
GeNN does not support custom event types in addition to the standard threshold
and reset, they can therefore not be used with the Brian2GeNN backend.

Heterogeneous delays
--------------------
At the moment, GeNN only has support for a single homogeneous delay for each
synaptic population. Brian simulations that use heterogeneous delays can
therefore not use the Brian2GeNN backend. In simple cases with just a few
different delay values (e.g. one set of connections with a short and another
set of connections with a long delay), this limitation can be worked around by
creating multiple ``Synapses`` objects with each using a homogeneous delay.

Multiple synaptic pathways
--------------------------
GeNN does not have support for multiple synaptic pathways as Brian 2 does, you
can therefore only use a single ``pre`` and ``post`` pathway with Brian2GeNN.

Timed arrays
------------
Timed arrays post a problem in the Brian2GeNN interface because they
necessitate communication from the timed array to the target group at
runtime that would result in host to GPU copies in the final CUDA/C++
code. This could lead to large inefficiences, the use of ``TimedArray`` is therefore
currently restricted to code in ``run_regularly`` operations that will be executed on
the CPU.

Multiple clocks
---------------
GeNN is by design operated with a single clock with a fixed time step
across the entire simulation. If you are using multiple clocks and
they are commensurate, please reformulate your script using just the
fastest clock as the standard clock. If your clocks are not
commensurate, and this is essential for your simulation, Brian2GeNN
can unfortunately not be used.

Multiple runs
-------------
GeNN is designed for single runs and cannot be used for the Brian style
multiple runs. However, if this is of use, code can be run repeatedly
"in multiple runs" that are completely independent. This just needs
``device.reinit()`` and ``device.activate()`` issued after the ``run(runtime)``
command.

Note, however, that these multiple runs are completely independent, i.e. for
the second run the code generation pipeline for Brian2GeNN is repeated in its
entirety which may incur a measurable delay.

Multiple networks
-----------------
Multiple networks cannot be supported in the Brian2GeNN
interface. Please use only a single network, either by creating it explicitly
as a ``Network`` object or by not creating any (i.e. using Brian's "magic"
system).

Custom schedules
----------------
GeNN has a fixed order of operations during a time step, Brian's more flexible
scheduling model (e.g. changing a network's schedule or individual objects'
``when`` attribute) can therefore not be used.
