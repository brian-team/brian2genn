from brian2 import *
import brian2genn

set_device('genn')

N = 5
Iin = 10
gNa= 120
ENa= 55
gK= 36
EK= -72
gl= 0.3
El= -50
C= 1
eqs = '''
dV/dt= (m**3*h*gNa*(ENa-V)+n**4*gK*(EK-V)+gl*(El-V)+Iin)/C/ms : 1
dm/dt= ((3.5+0.1*V)/(1-exp(-3.5-0.1*V))*(1-m)-4*exp(-(V+60)/18)*m)/ms : 1
dh/dt= (0.07*exp(-V/20-3)*(1-h)-1/(exp(-3-0.1*V)+1)*h)/ms : 1
dn/dt= ((-0.5-0.01*V)/(exp(-5-0.1*V)-1)*(1-n)-0.125*exp(-(V+60)/80)*n)/ms : 1
'''
G = NeuronGroup(N, eqs, threshold='V> 0', reset='')

run(500*ms)

device.build(project_dir='simple_example_HH',
             compile_project=True,
             run_project=True,
             use_GPU=False)
