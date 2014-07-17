import numpy
import os
from subprocess import call
import inspect
from collections import defaultdict

from brian2.units import second
from brian2.codegen.generators.cpp_generator import c_data_type
from brian2.core.clocks import defaultclock
from brian2.core.preferences import brian_prefs
from brian2.core.variables import *
from brian2.core.network import Network
from brian2.devices.device import Device, set_device, all_devices
from brian2.devices.cpp_standalone.device import CPPStandaloneDevice
from brian2.synapses.synapses import Synapses
from brian2.utils.filetools import copy_directory, ensure_directory, in_directory
from brian2.utils.stringtools import word_substitute
from brian2.memory.dynamicarray import DynamicArray, DynamicArray1D
from brian2.groups.neurongroup import *

from .codeobject import GeNNCodeObject

__all__ = ['GeNNDevice']

def decorate(code, variables, parameters):
    # this is a bit of a hack, it should be part of the language probably
    for v in variables:
        code = word_substitute(code, {v[0] : '$('+v[0]+')'})
    for p in parameters:
        code = word_substitute(code, {p : '$('+p+')'})
    code= word_substitute(code, {'dt' : 'DT'}).strip()
    code= code.replace('\n', '\\n\\\n')
    code = code.replace('"', '\\"')
    return code

class neuronModel(object):
    '''
    '''
    def __init__(self):
        self.name=''
        self.N= 0
        self.variables= [ ]
        self.parameters= [ ]
        self.pvalue= [ ]
        self.code_lines= [ ]
        self.thresh_cond_lines= [ ]
        self.reset_code_lines= [ ]

class GeNNDevice(CPPStandaloneDevice):
    '''
    '''
    def __init__(self):
        self.neuron_models = [ ]
        self.run_duration = None
        super(GeNNDevice, self).__init__()        

    def build(self, project_dir='output', compile_project=True, run_project=True, use_GPU=True):

        # Check for GeNN compatibility
        
        if len(self.dynamic_arrays) or len(self.dynamic_arrays_2d):
            raise NotImplementedError("GeNN does not support objects that use dynamic arrays (Synapses, SpikeMonitor, etc.)")
                
        networks = [net() for net in Network.__instances__() if net().name!='_fake_network']
        synapses = [S() for S in Synapses.__instances__()]

        if len(synapses):
            raise NotImplementedError("GeNN does not support Synapses (yet).")
        
        if len(networks)!=1:
            raise NotImplementedError("GeNN only supports a signle Network object")
        net = networks[0]

        # Start building the project

        self.project_dir = project_dir
        ensure_directory(project_dir)
        
        objects = dict((obj.name, obj) for obj in net.objects)
        neuron_groups = [obj for obj in net.objects if isinstance(obj, NeuronGroup)]
        
        # assemble the model descriptions:
        self.model_name= net.name+'_model'
        for obj in neuron_groups:
            # Extract the variables
            neuron_model= neuronModel()
            neuron_model.name= obj.name
            neuron_model.N= obj.N
            for k, v in obj.variables.iteritems():
                if k == '_spikespace' or k == 't' or k == 'dt':
                    pass
                elif isinstance(v, ArrayVariable):
                    neuron_model.variables.append((k, c_data_type(v.dtype)))
   
            for suffix, lines in [('_stateupdater', neuron_model.code_lines),
                                  ('_thresholder', neuron_model.thresh_cond_lines),
                                  ('_resetter', neuron_model.reset_code_lines),
                                  ]:
                codeobj = objects[obj.name+suffix].codeobj
                for k, v in codeobj.variables.iteritems():
                    if k == 'dt':
                        self.dtDef= '#define DT '+repr(getattr(v.obj, v.attribute))
                    elif isinstance(v, Constant):
                        if k not in neuron_model.parameters:
                            neuron_model.parameters.append(k)
                            neuron_model.pvalue.append(repr(v.value)) 
                      
                code = decorate(codeobj.code, neuron_model.variables, neuron_model.parameters).strip()
                lines.append(code)                    
            
            self.neuron_models.append(neuron_model)
        
        model_tmp = GeNNCodeObject.templater.model(None, None,
                                                   neuron_models= self.neuron_models,
                                                   dtDef= self.dtDef,
                                                   model_name= self.model_name,
                                                   )
        open(os.path.join(project_dir,self.model_name+'.cc'), 'w').write(model_tmp)

        runner_tmp = GeNNCodeObject.templater.runner(None, None,
                                                     neuron_models= self.neuron_models,
                                                     model_name= self.model_name,
                                                     )        
        open(os.path.join(project_dir, 'runner.cu'), 'w').write(runner_tmp.cpp_file)
        open(os.path.join(project_dir, 'runner.h'), 'w').write(runner_tmp.h_file)
        engine_tmp = GeNNCodeObject.templater.engine(None, None,
                                                     neuron_models= self.neuron_models,
                                                     model_name= self.model_name,
                                                     )        
        open(os.path.join(project_dir, 'engine.cc'), 'w').write(engine_tmp.cpp_file)
        open(os.path.join(project_dir, 'engine.h'), 'w').write(engine_tmp.h_file)

        Makefile_tmp= GeNNCodeObject.templater.Makefile(None, None,
                                                        neuron_models= self.neuron_models,
                                                        model_name= self.model_name,
                                                        ROOTDIR=os.path.abspath(project_dir)
                                                        ) 
        open(os.path.join(project_dir, 'Makefile'), 'w').write(Makefile_tmp)

        if compile_project:
            call(["buildmodel", self.model_name], cwd=project_dir)
            call(["make"], cwd=project_dir)
        if run_project:
            gpu_arg = "1" if use_GPU else "0"
            call(["bin/linux/release/runner", "test",
                  str(self.run_duration), gpu_arg], cwd=project_dir)

    def code_object_class(self, codeobj_class=None):
        if codeobj_class is not None:
            raise ValueError("Cannot specify codeobj_class for GeNN device.")
        return GeNNCodeObject

    def network_run(self, net, duration, report=None, report_period=10*second,
                    namespace=None, level=0):
        net.before_run(run_namespace=namespace, level=level+2)
        if self.run_duration is not None:
            raise NotImplementedError('Only a single run statement is supported.')
        self.run_duration = float(duration)


genn_device = GeNNDevice()

all_devices['genn'] = genn_device

