'''
Created on 28 Oct 2014

@author: Dan
'''
from brian2 import *
import brian2genn

set_device('genn')

G = NeuronGroup(10, 'dv/dt=-v/second : 1\nu:1', threshold='v>1', reset='v=0',
                name='TheNG')
S = Synapses(G, G, 'w:1', pre='v += w*w*w; w=5',
             post='w=1',
             name='TheSynapses')
S.connect()
run(10*ms)
