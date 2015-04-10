from brian2 import *
import brian2genn

set_device('genn')

N = 10000
tau = 10*ms
Iin = 0.11/ms 
eqs = '''
dV/dt = -V/tau + Iin : 1
'''
G = NeuronGroup(N, eqs, threshold='V>1', reset='V=0', refractory=5 * ms)

run(10*ms)

device.build(directory='simple_example',
             compile=True,
             run=True,
             use_GPU=True)
