from brian2 import *
import brian2genn

set_device('genn', directory='testSummedVars', use_GPU= False)
#set_device('cpp_standalone')


neurons = NeuronGroup(1, """dv/dt = (g-v)/(10*ms) : 1
                            g : 1""", method='exact')
H = NeuronGroup(10, 'V:1')

S = Synapses(H, neurons,'''
                dg_syn/dt = -g_syn/(100*ms) : 1 (clock-driven)
                g_post = g_syn : 1 (summed)''')


S.connect(True)
run(101*ms)
