from brian2 import *
import brian2genn

set_device('genn', directory='simple_example_synapses')
#set_device('cpp_standalone')

N = 100
tau = 10*ms
eqs = '''
dV/dt = -V/tau + Iin/tau : 1
Iin : 1
'''
G = NeuronGroup(N, eqs, threshold='V>1', reset='V=0', name='PN')
G.V = rand()
G2 = NeuronGroup(N, eqs, threshold='V>1', reset='V=0', name='LN')
G2.V = 2 * rand()

alpha = 20/ms
beta = 30/ms
S = Synapses(G, G2,
             model='''
            ds/dt= alpha*(1-s) - beta*s: 1
            g: 1
            ''',
             pre='Iin_post+= g',
             name='ex_syns')

alpha2 = 40/ms
beta2 = 60/ms
p_post = 1
p_pre = 30
S2 = Synapses(G2, G,
              model='''
             ds/dt= alpha2*(1-s) - beta2*s: 1
             g: 1
             ''',
              pre='Iin_post+= g*p_pre',
              post='''
             g*= p_post-0.9;
             ''',
              name='inh_syns')

S.connect(i=1, j=5)
S2.connect(i=[1, 2], j=[1, 2])

S.g = 'rand()'

run(100*ms)
