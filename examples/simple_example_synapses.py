from brian2 import *
import brian2genn

set_device('genn')
#set_device('cpp_standalone')

N = 1000000
tau = 10*ms
Iin = 0.11/ms 
eqs = '''
dV/dt = -V/tau + Iin : 1
'''
G = NeuronGroup(N, eqs, threshold='V>1', reset='V=0')

alpha= 20*ms
beta= 30*ms

S= Synapses(G, G, model='''
ds/dt= alpha*(1-s) - beta*s: 1
g: 1
''',
pre='s+= g')

alpha2= 40*ms
beta2= 60*ms

S2= Synapses(G, G, model='''
ds/dt= alpha2*(1-s) - beta2*s: 1
g: 1
''',
pre='s+= g',
post='s-=g')

run(100*ms)

S.connect(1,5);
S.connect('i != j', n=2);
S.connect([1, 2],[1, 2]);

# this fails: I kind of understand why - but how is it supposed to be done?
S.g= 'rand()'
print('Type of S.g') 
print(type(S.g))

device.build(project_dir='simple_example_synapses',
             compile_project=True,
             run_project=True,
             use_GPU=True)

#device.build(project_dir='simple_example_synapses',
#             compile_project=True,
#             run_project=True)
