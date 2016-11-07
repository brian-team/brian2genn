How Brian2GeNN works inside
===========================

The Brian2GeNN interface is providing middleware to use the GeNN
simulator framework as a backend to the Brian 2 simulator. It has been
designed in a way that makes maximal use of the existing Brian 2 code
base by deriving large parts of the generated code from the
``cpp_standalone`` device of Brian 2.

Model and user code in GeNN
---------------------------

In GeNN a simulation is assembled from two main sources of code. Users
of GeNN provide "code snippets" as C++ strings that define neuron and
synapse models. These are then assembled into neuronal networks in a
model definition function. Based on the mdoel definition, GeNN
generates GPU and equivalent CPU simulation code for the described
network. This is the first source of code. 

The actual simulation and
handling input and output data is the responsibility of the user in
GeNN. Users provide their own C/C++ code for this that utilizes the
generated code described above for the core simulation but is otherwise
fully independent of the core GeNN system.

In the Brian2GeNN both the model definition and the user code for the
main simulation are derived from the Brian 2 model description. The
user side code for data handling etc derives more or less directly
from the Brian 2 `cpp_standalone` device in the form of
`GennUserCodeObjects`. The model definition code and 
"code snippets" derive from separate templates and are capsulated into
`GeNNCodeObjects`. 


Code generation pipeline in Brian2GeNN
--------------------------------------

The model generation pipeline in Brian2GeNN involves a number of
steps. First, Brian 2 performs the usual interpretation of equations
and unit checking, as well as, applying an integration scheme onto
ODEs. The resulting abstract code is then translated into C++ code for
`GeNNUserCodeObjects` and C++-like code for `GeNNCodeObjects`. These
are then assembled using templating in Jinja2 into C++ code and GeNN
model definition code. The details of making Brian 2's ``cpp_standalone``
code suitable for the GeNN user code and GeNN model definition code
and code snippets are taken care of in the `GeNNDevice.build`
function.

Once all the sources have been generated, the resulting GeNN project
is built with the GeNN code generation pipeline. See the GeNN manual for
more details on this process.

Templates in Brian2GeNN
-----------------------

The templates used for code generation in Brian2GeNN, as mentioned
above, partially derive from the ``cpp_standalone`` templates of
Brian 2. More than half of the templates are identical. Other
templates, however, in particular for the model definition file and
the main simulation engine and main entry file "runner.cc" have been
specifically written for Brian2GeNN to produce a valid GeNN project.

Data transfers and results
--------------------------

In Brian 2, data structures for initial values and synaptic
connectivities etc are written to disk into binary files if a
standalone device is used. The executable of the standalone device
then reads the data from disk and initializes its variables with it.
In Brian2GeNN the same mechanism is used, and after the data has been
read from disk with the native ``cpp_standalone`` methods, there is a
translation step, where Brian2GeNN provides code that translates the
data from ``cpp_standalone`` arrays into the appropriate GeNN data
structures. The methods for this process are provided in the static
(not code-generated) "b2glib".
 
At the end of a simulation, the inverse process takes place and GeNN
data is transfered back into ``cpp_standalone`` arrays. Native Brian 2
``cpp_standalone`` code is then invoked to write data back to disk.

If monitors are used, the translation occurs at every instance when
monitors are updated. 

Memory usage
------------

Related to the implementation of data flows in Brian2GeNN described
above the host memory used in a run in brian2GeNN is about twice what
would have been used in a Brian 2 native ``cpp_standalone``
implementation because all data is held in two different formats - as
``cpp_standalone`` arrays and as GeNN data structures.
