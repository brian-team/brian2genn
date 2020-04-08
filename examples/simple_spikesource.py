from brian2 import *
import brian2genn

set_device('genn', directory='simple_spikesource')
#set_device('cpp_standalone')

G = NeuronGroup(10, 'v:1')
mon = StateMonitor(G, 'v', record=True)
indices = np.array([3, 2, 1, 1, 4, 5])
times = np.array([6, 5, 4, 3, 3, 1]) * ms
SG = SpikeGeneratorGroup(10, indices, times)
mon2 = SpikeMonitor(SG, record=True)
S = Synapses(SG, G, on_pre='v+=1')
S.connect(j='i')
run(7*ms)
