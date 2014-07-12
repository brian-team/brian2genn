import numpy
import os
import inspect
from collections import defaultdict

from brian2.units import second
from brian2.core.clocks import defaultclock
from brian2.devices.device import Device, set_device, all_devices
from brian2.devices.cpp_standalone.device import CPPStandaloneDevice
from brian2.core.preferences import brian_prefs
from brian2.core.variables import *
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
    code= word_substitute(code, {'dt' : 'DT'});
    code= code.replace('\n', '\\n\\\n')
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
        super(GeNNDevice, self).__init__()        

    def build(self, project_dir='output'):

        if len(self.dynamic_arrays) or len(self.dynamic_arrays_2d):
            raise NotImplementedError("GeNN does not support objects that use dynamic arrays (Synapses, SpikeMonitor, etc.)")
        
        self.project_dir = project_dir
        ensure_directory(project_dir)        
        
        raise NotImplementedError
    
        ######### WHAT FOLLOWS IS THE GENN CODE THAT THOMAS NOWOTNY WROTE IN 2013
        ######### This needs to be updated to work with the changes in Brian's standalone design
        ######### To do so, I derived the class from CPPStandaloneDevice so that we only need to rewrite the
        ######### build() method, following the way it is done in CPPStandaloneDevice.build.
       
        # assemble the model descriptions:
        self.model_name= net.name+'_model'
        for obj in net.objects:
            # Extract the variables
            if isinstance(obj, NeuronGroup):
#                print 'we have a neuron group'
                neuron_model= neuronModel();
                neuron_model.name= obj.name
                neuron_model.N= obj.N
                for k, v in obj.variables.iteritems():
                    if k == '_spikespace' or k == 't' or k == 'dt':
                        pass
                    else:
                        neuron_model.variables.append((k, c_data_type(v.dtype)))
       
                trgnm= obj.name+'_stateupdater'
                for obj2 in net.objects:
                    if obj2.name == trgnm:
                        updater= obj2.updaters[0]
                        codeobj= updater.owner
                        for k, v in codeobj.namespace.iteritems():
                            if k == 'dt':
                                self.dtDef= '#define DT '+repr(v)
                            elif isinstance(v, (int, float)):
                                if k not in neuron_model.parameters:
                                    neuron_model.parameters.append(k)
                                    neuron_model.pvalue.append(repr(v)) 
                              
                        code = decorate(codeobj.code.cpp_file, neuron_model.variables, neuron_model.parameters)
                        neuron_model.code_lines.append(code)                    
                trgnm= obj.name+'_thresholder'
                for obj2 in net.objects:
                    if obj2.name == trgnm:
                        for updater in obj2.updaters:
                            codeobj= updater.owner
                            for k, v in codeobj.namespace.iteritems():
                                if k == 'dt':
                                    self.dtDef= '#define DT '+repr(v)
                                elif isinstance(v, (int, float)):
                                    if k not in neuron_model.parameters:
                                        neuron_model.parameters.append(k)
                                        neuron_model.pvalue.append(repr(v)) 
                            code = decorate(codeobj.code.cpp_file, neuron_model.variables, neuron_model.parameters)
                            print code
                            neuron_model.thresh_cond_lines.append(code)  
                trgnm= obj.name+'_resetter'
                for obj2 in net.objects:
                    if obj2.name == trgnm:
                        for updater in obj2.updaters:
                            codeobj= updater.owner
                            for k, v in codeobj.namespace.iteritems():
                                if k == 'dt':
                                    self.dtDef= '#define DT '+repr(v)
                                elif isinstance(v, (int, float)):
                                    if k not in neuron_model.parameters:
                                        neuron_model.parameters.append(k)
                                        neuron_model.pvalue.append(repr(v)) 
                            code = decorate(codeobj.code.cpp_file, neuron_model.variables, neuron_model.parameters)
                            neuron_model.reset_code_lines.append(code)  
                
#                if (hasattr(obj, 'threshold')):
#                    if (obj.threshold <> None):
#                        code = decorate(obj.threshold, neuron_model.variables, neuron_model.parameters)
#                        neuron_model.thresh_cond_lines.append(code)
                self.neuron_models.append(neuron_model)
        
        # The code_objects are passed in the right order to run them because they were
        # sorted by the Network object. To support multiple clocks we'll need to be
        # smarter about that.
        print self.neuron_models
        #print self.neuron_models[2].code_lines
        model_tmp = GeNNCodeObject.templater.model(None,
                                                   neuron_models= self.neuron_models,
                                                   dtDef= self.dtDef,
                                                   model_name= self.model_name,
                                                   )
        open('output/'+self.model_name+'.cc', 'w').write(model_tmp)

        runner_tmp = GeNNCodeObject.templater.runner(None,
                                                     neuron_models= self.neuron_models,
                                                     model_name= self.model_name,
                                                                  )        
        open('output/runner.cu', 'w').write(runner_tmp.cpp_file)
        open('output/runner.h', 'w').write(runner_tmp.h_file)
        engine_tmp = GeNNCodeObject.templater.engine(None,
                                                     neuron_models= self.neuron_models,
                                                     model_name= self.model_name,                                                              )        
        open('output/engine.cc', 'w').write(engine_tmp.cpp_file)
        open('output/engine.h', 'w').write(engine_tmp.h_file) 

        Makefile_tmp= GeNNCodeObject.templater.Makefile(None,
                                                        neuron_models= self.neuron_models,
                                                        model_name= self.model_name,                                                              ) 
        open('output/Makefile', 'w').write(Makefile_tmp);

        # Copy the brianlibdirectory
        brianlib_dir = os.path.join(os.path.split(inspect.getsourcefile(GeNNCodeObject))[0],
                                    'brianlib')
        copy_directory(brianlib_dir, 'output/brianlib')


genn_device = GeNNDevice()

all_devices['genn'] = genn_device

