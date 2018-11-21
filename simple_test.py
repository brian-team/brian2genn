from brian2 import *
import brian2genn
set_device("genn", with_output=True, use_GPU=False, debug=True)
group = NeuronGroup(5, "dv/dt = -v/(10*ms) : 1")
run(1*ms)
