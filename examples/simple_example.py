from brian2 import *
import brian2.devices.genn

set_device('genn')

N = 100
tau = 10*ms
eqs = '''
dv/dt = -v/tau : 1
'''
G = NeuronGroup(N, eqs, threshold='v>1', reset='v=0')

run(100*ms)
