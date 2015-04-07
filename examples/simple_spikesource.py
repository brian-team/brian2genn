from brian2 import *
import brian2genn

set_device('genn')
#set_device('cpp_standalone')

G = NeuronGroup(10, 'v:1')
mon = StateMonitor(G, 'v', record=True)
indices = np.array([3, 2, 1, 1, 4, 5])
times =   np.array([6, 5, 4, 3, 3, 1]) * ms
SG = SpikeGeneratorGroup(10, indices, times)
S = Synapses(SG, G, pre='v+=1', connect='i==j')
run(7*ms)

device.build(directory='simple_spikesource',
             compile=True,
             run=True,
             use_GPU=True)

#device.build(directory='simple_statemon',
#             compile=True,
#             run=True)

