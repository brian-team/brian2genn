from brian2 import *
import brian2genn

set_device('genn', directory='shortEx')
#set_device('cpp_standalone')

tau = 5*ms
eqs = '''
dV/dt = k/tau : 1
k : 1
'''
G = NeuronGroup(10, eqs, threshold='V>1', reset='V=0')
G.k = linspace(1, 5, len(G))
H = NeuronGroup(10, 'V:1')
S = Synapses(H, G, post='V_pre += 1')
S.connect(j='i')
run(101*ms)
