from brian2 import *
import brian2genn

set_device('genn', directory='simple_example_HH')

N = 50000
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
dm/dt= ((3.5+0.1*V)/(1-exp(-3.5-0.1*V))*(1.0-m)-4.0*exp(-(V+60.0)/18.0)*m)/ms : 1
dh/dt= (0.07*exp(-V/20.0-3.0)*(1.0-h)-1.0/(exp(-3.0-0.1*V)+1.0)*h)/ms : 1
dn/dt= ((-0.5-0.01*V)/(exp(-5.0-0.1*V)-1)*(1.0-n)-0.125*exp(-(V+60.0)/80.0)*n)/ms : 1
'''
G = NeuronGroup(N, eqs, threshold='V> 0', reset='', method='exponential_euler')

run(500*ms)
