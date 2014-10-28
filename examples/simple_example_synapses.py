from brian2 import *
import brian2genn

set_device('genn')
#set_device('cpp_standalone')

N = 1000
tau = 10*ms
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
            pre='Iin_post+= g*(tanh(V-10))',
            name='ex_syns')

alpha2= 40*ms
beta2= 60*ms
p_post= 1
p_pre= 30
S2= Synapses(G2, G, 
             model='''
             ds/dt= alpha2*(1-s) - beta2*s: 1
             g: 1
             ''',
             pre='Iin_post+= g*p_pre',
             post='''
             g*= p_post-0.9;
             ''',
             name='inh_syns')

S.connect(1,5);
S.connect('i != j', n=2);
S.connect([1, 2],[1, 2]);

S.g= 'rand()'

run(100*ms)

device.build(directory='simple_example_synapses',
            compile=True,
             run=True,
             use_GPU=True)

#device.build(directory='simple_example_synapses',
#             compile=True,
#             run=True)

