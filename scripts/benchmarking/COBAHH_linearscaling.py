#!/usr/bin/env python

"""
This is an implementation of a benchmark described
in the following review paper:

Simulation of networks of spiking neurons: A review of tools and strategies (2006).
Brette, Rudolph, Carnevale, Hines, Beeman, Bower, Diesmann, Goodman, Harris, Zirpe,
Natschlaeger, Pecevski, Ermentrout, Djurfeldt, Lansner, Rochel, Vibert, Alvarez, Muller,
Davison, El Boustani and Destexhe.
Journal of Computational Neuroscience

Benchmark 3: random network of HH neurons with exponential synaptic conductances

Clock-driven implementation
(no spike time interpolation)

R. Brette - Dec 2007
"""

from brian2 import *
import brian2genn
import sys

extra_args = {}

if len(sys.argv)<=2:
    if len(sys.argv)==1:
        scale = 1.0
    else:
        scale = float(sys.argv[1])
    device = 'cpp_standalone'
    threads = 1
    use_spikemon = True
    do_run = True
    run_it_for = 1.0
    debugmode = True
else:
    scale = float(sys.argv[1])
    device = sys.argv[2]
    threads = int(sys.argv[3])
    use_spikemon = sys.argv[4] == 'true'
    do_run = sys.argv[5] == 'true'
    run_it_for = double(sys.argv[6])
    debugmode = False

if threads == -1:
    extra_args = {'use_GPU': False}
else:
    prefs.devices.cpp_standalone.openmp_threads = threads
set_device(device, **extra_args)

if device == 'genn':
    prefs.devices.genn.auto_choose_device = False
    prefs.devices.genn.default_device = 0
    prefs.devices.genn.benchmarking = True

print 'Running with arguments: ', sys.argv

# Parameters
area = 20000 * umetre ** 2
Cm = (1 * ufarad * cm ** -2) * area
gl = (5e-5 * siemens * cm ** -2) * area

El = -60 * mV
EK = -90 * mV
ENa = 50 * mV
g_na = (100 * msiemens * cm ** -2) * area
g_kd = (30 * msiemens * cm ** -2) * area
VT = -63 * mV
# Time constants
taue = 5 * ms
taui = 10 * ms
# Reversal potentials
Ee = 0 * mV
Ei = -80 * mV
we = 6 * nS  # excitatory synaptic weight
wi = 67 * nS  # inhibitory synaptic weight

# The model
eqs = Equations('''
dv/dt = (gl*(El-v)+ge*(Ee-v)+gi*(Ei-v)-
         g_na*(m*m*m)*h*(v-ENa)-
         g_kd*(n*n*n*n)*(v-EK))/Cm : volt
dm/dt = alpha_m*(1-m)-beta_m*m : 1
dn/dt = alpha_n*(1-n)-beta_n*n : 1
dh/dt = alpha_h*(1-h)-beta_h*h : 1
dge/dt = -ge*(1./taue) : siemens
dgi/dt = -gi*(1./taui) : siemens
alpha_m = 0.32*(mV**-1)*(13*mV-v+VT)/
         (exp((13*mV-v+VT)/(4*mV))-1.)/ms : Hz
beta_m = 0.28*(mV**-1)*(v-VT-40*mV)/
        (exp((v-VT-40*mV)/(5*mV))-1)/ms : Hz
alpha_h = 0.128*exp((17*mV-v+VT)/(18*mV))/ms : Hz
beta_h = 4./(1+exp((40*mV-v+VT)/(5*mV)))/ms : Hz
alpha_n = 0.032*(mV**-1)*(15*mV-v+VT)/
         (exp((15*mV-v+VT)/(5*mV))-1.)/ms : Hz
beta_n = .5*exp((10*mV-v+VT)/(40*mV))/ms : Hz
''')

P = NeuronGroup(int(4000 * scale), model=eqs, threshold='v>-20*mV', refractory=3 * ms,
                method='exponential_euler')
Pe = P[:int(3200 * scale)]
Pi = P[int(3200 * scale):]
Ce = Synapses(Pe, P, on_pre='ge+=we')
Ci = Synapses(Pi, P, on_pre='gi+=wi')
Ce.connect(p=80./len(P))
Ci.connect(p=80./len(P))

# Initialization
P.v = 'El + (randn() * 5 - 5)*mV'
P.ge = '(randn() * 1.5 + 4) * 10.*nS'
P.gi = '(randn() * 12 + 20) * 10.*nS'

# Record a few traces
if use_spikemon:
    trace = StateMonitor(P, 'v', record=[1, 10, 100])
if debugmode:
    spikemon = SpikeMonitor(P)
    popratemon = PopulationRateMonitor(P)

import time

if do_run:
    runtime = run_it_for * second
else:
    runtime = 0 * second

start = time.time()
run(runtime, report='text')
took = (time.time() - start)
print 'took %.1fs' % took
neurons = int(4000 * scale)
synapses = len(Ce) + len(Ci)
devNo = {'genn': 0, 'cpp_standalone': 1}
dev = devNo[device]
intfrombool = {False: 0, True: 1}
uSpkmon = intfrombool[use_spikemon]
run = intfrombool[do_run]
if device == 'genn':
    with open('benchmarks_COBAHH_linearscaling.txt', 'a') as f:
        data = [neurons, synapses, dev, threads, uSpkmon, run, run_it_for, took]
        f.write('\t'.join('%s' % d for d in data) + '\t')
        with open('GeNNworkspace/test_output/test.time', 'r') as bf:
            for line in bf:
                line = line.strip()
                line = '\t'.join('%s' % item for item in line.split(' ')) + '\n'
                f.write(line)
elif not debugmode:
    with open('benchmarks_COBAHH_linearscaling_cpp.txt', 'a') as f:
        data = [neurons, synapses, dev, threads, uSpkmon, run, run_it_for, took]
        f.write('\t'.join('%s' % d for d in data) + '\n')
else:
    print 'Number of spikes:', spikemon.num_spikes
    print 'Mean firing rate: %.1f Hz' % (spikemon.num_spikes/(runtime*len(P)))
    subplot(311)
    plot(spikemon.t/ms, spikemon.i, ',k')
    subplot(312)
    plot(trace.t/ms, trace.v[:].T)
    subplot(313)
    plot(popratemon.t/ms, popratemon.smooth_rate(width=1*ms))
    show()

