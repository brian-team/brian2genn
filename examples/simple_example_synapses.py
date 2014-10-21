from brian2 import *
import brian2genn

set_device('genn')
#set_device('cpp_standalone')

N = 1000
tau = 10*ms
Iin = 0.11/ms 
eqs = '''
dV/dt = -V/tau + Iin : 1
'''
G = NeuronGroup(N, eqs, threshold='V>1', reset='V=0', name='PN')
G2= NeuronGroup(N, eqs, threshold='V>1', reset='V=0', name='LN')

alpha= 20*ms
beta= 30*ms
S= Synapses(G, G2, 
            model='''
            ds/dt= alpha*(1-s) - beta*s: 1
            g: 1
            ''',
            pre='s+= g',
            name='ex_syns')

alpha2= 40*ms
beta2= 60*ms
S2= Synapses(G2, G, 
             model='''
             ds/dt= alpha2*(1-s) - beta2*s: 1
             g: 1
            ''',
             pre='s+= g',
             post='Ipost= -g*(V_post+1)',
             name='inh_syns')

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
