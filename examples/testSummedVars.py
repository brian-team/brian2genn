from brian2 import *
import brian2genn

set_device('genn', directory='testSummedVars')
# set_device('cpp_standalone')

neurons = NeuronGroup(1, """dv/dt = (g-v)/(10*ms) : 1
                            g : 1""", method='exact', threshold='v > 0.1', reset='v= 0')
neurons.g = 0.2
H = NeuronGroup(10, 'V:1', threshold='V > 0.5', reset='')

S = Synapses(neurons, H, '''
                dg_syn/dt = -g_syn/(100*ms) : 1 (clock-driven)
                V_post = g_syn : 1 (summed)''', on_pre='g_syn= g_syn+1')
S.connect(True)
mon = StateMonitor(S, variables=True, record=range(10))
mon2 = StateMonitor(neurons, variables=True, record=True)
mon3 = StateMonitor(H, variables=True, record=True)
run(101 * ms)

plot(mon3.t, mon3.V.T)
show()
