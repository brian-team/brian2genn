from brian2 import *
import brian2genn

set_device('genn', directory='simple_example')

Npre = 10
Npost= 10
tau = 10*ms
Iin = 0.11/ms 
eqs = '''
dV/dt = -V/tau + Iin : 1
'''
G = NeuronGroup(Npre, eqs, threshold='V>1', reset='V=0', refractory=5 * ms)
G2= NeuronGroup(Npost, eqs, threshold='V>1', reset='V=0', refractory=5 * ms)

S =Synapses(G, G2, 'w:1', on_pre='V+= w')
S.connect(i=np.array([1, 3, 4, 2]), j=np.array([2, 2, 2, 2]))
S.connect(i=[1,2], j=[1,1])
run(10*ms)
