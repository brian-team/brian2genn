Brian2GeNN specific preferences
===============================

Connectivity
------------------
The preference ``prefs.devices.genn.conncetivity`` determines what
connectivity scheme is used within GeNN to represent the connections
between neurons. GeNN supports the use of full connectivity matrices
('DENSE') or a representation where connections are represented with
sparse matrix methods ('SPARSE'). When this preference is set to
'AUTO', a separately defined logic expression determines wheter
'DENSE' or 'SPARSE' are used for each individula Synapses population.
This logic expression can be set with the
``prefs.devices.genn.connectivity_decision`` preference.


Connectivity_decision
----------------------
The ``prefs.devices.genn.connectivity_decision`` contains a logical
expression that determines whether to use 'DENSE' or 'SPARSE' matrix
methods in GeNN for a given matrix. 'DENSE' is used when the condition
evaluates to ``True`` and 'SPARSE' is used otherwise. It's standard
value is ``Nsyn > 0.25*Npre*Npost``, i.e. 'DENSE' is used whenever the
number of actually existing synaptic connections is larger than a
quarter of all possible synaptic connections between the pre- and
post-synaptic populations. 

Compiler options
-----------------

