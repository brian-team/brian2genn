from brian2 import *
import brian2genn

set_device('genn')

N = 1000000
tau = 10*ms
Iin = 0.11/ms 
eqs = '''
dV/dt = -V/tau + Iin : 1
'''
G = NeuronGroup(N, eqs, threshold='V>1', reset='V=0')

run(100*ms)

device.build(project_dir='simple_example',
             compile_project=True,
             run_project=True,
             use_GPU=True)
