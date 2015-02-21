import pprint
import numpy
import numpy as np
import os
from subprocess import call
import inspect
import shutil
from collections import defaultdict

from brian2.units import second
from brian2.units import have_same_dimensions
from brian2.codegen.generators.cpp_generator import c_data_type
from brian2.codegen.templates import MultiTemplate
from brian2.core.clocks import defaultclock
from brian2.core.preferences import brian_prefs
from brian2.core.variables import *
from brian2.core.network import Network
from brian2.devices.device import Device, set_device, all_devices
from brian2.devices.cpp_standalone.device import CPPStandaloneDevice
from brian2.synapses.synapses import Synapses
from brian2.monitors.spikemonitor import SpikeMonitor
from brian2.monitors.statemonitor import StateMonitor
from brian2.utils.filetools import copy_directory, ensure_directory, in_directory
from brian2.utils.stringtools import word_substitute
from brian2.memory.dynamicarray import DynamicArray, DynamicArray1D
from brian2.groups.neurongroup import *
from brian2.utils.logger import get_logger
from brian2.devices.cpp_standalone.codeobject import CPPStandaloneCodeObject
from brian2 import prefs
from .codeobject import GeNNCodeObject, GeNNUserCodeObject
from brian2.core.magic import _get_contained_objects

__all__ = ['GeNNDevice']

logger = get_logger(__name__)
prefs['codegen.generators.cpp.restrict_keyword']= '__restrict'

def freeze(code, ns):
    # this is a bit of a hack, it should be passed to the template somehow
    for k, v in ns.items():
        if isinstance(v, (int, float)): # for the namespace provided for functions
            code = word_substitute(code, {k: str(v)})
        elif (isinstance(v, Variable) and not isinstance(v, AttributeVariable) and
              v.scalar and v.constant and v.read_only):
            value = v.get_value()
            if value < 0:
                string_value = '(%r)' % value
            else:
                string_value = '%r' % value
            code = word_substitute(code, {k: string_value})
    return code

def decorate(code, variables, parameters, do_final= True):
    # this is a bit of a hack, it should be part of the language probably
    for v in variables:
        code = word_substitute(code, {v : '$('+v+')'})
    for p in parameters:
        code = word_substitute(code, {p : '$('+p+')'})
    code= word_substitute(code, {'dt' : 'DT'}).strip()
    if do_final: 
        code= code.replace('\n', '\\n\\\n')
        code = code.replace('"', '\\"')
        code = word_substitute(code, {'addtoinSyn' : '$(addtoinSyn)'})
        code = word_substitute(code, {'_hidden_weightmatrix' : '$(_hidden_weightmatrix)'})
    return code

class neuronModel(object):
    '''
    '''
    def __init__(self):
        self.name=''
        self.N= 0
        self.variables= []
        self.variabletypes= []
        self.parameters= []
        self.pvalue= []
        self.code_lines= []
        self.thresh_cond_lines= []
        self.reset_code_lines= []

class synapseModel(object):
    '''
    '''
    def __init__(self):
        self.name=''
        self.srcname=''
        self.srcN= 0
        self.trgname=''
        self.trgN= 0
        self.N= 0
        self.variables= []
        self.variabletypes= []
        self.external_variables= []
        self.parameters= []
        self.pvalue= []
        self.simCode= []
        self.simLearnPost= []
        self.synapseDynamics= []
        self.postsyn_variables= []
        self.postsyn_variabletypes= []
        self.postsyn_parameters= []
        self.postsyn_pvalue= []
        self.postsSynDecay= []
        self.postSyntoCurrent= []

class spikeMonitorModel(object):
    '''
    '''
    def __init__(self):
        self.name=''
        self.neuronGroup=''

class stateMonitorModel(object):
    '''
    '''
    def __init__(self):
        self.name=''
        self.neuronGroup=''

class CPPWriter(object):
    def __init__(self, project_dir):
        self.project_dir = project_dir
        self.source_files = []
        self.header_files = []
        
    def write(self, filename, contents):
        logger.debug('Writing file %s:\n%s' % (filename, contents))
        if filename.lower().endswith('.cpp'):
            self.source_files.append(filename)
        elif filename.lower().endswith('.h'):
            self.header_files.append(filename)
        elif filename.endswith('.*'):
            self.write(filename[:-1]+'cpp', contents.cpp_file)
            self.write(filename[:-1]+'h', contents.h_file)
            return
        fullfilename = os.path.join(self.project_dir, filename)
        if os.path.exists(fullfilename):
            if open(fullfilename, 'r').read()==contents:
                return
        open(fullfilename, 'w').write(contents)

class GeNNDevice(CPPStandaloneDevice):
    '''
    '''
    def __init__(self):
        super(GeNNDevice, self).__init__()        
        self.neuron_models = []
        self.synapse_models = []
        self.spike_monitor_models= []
        self.state_monitor_models= []
        self.run_duration = None
         #: Dictionary mapping `ArrayVariable` objects to their globally
        #: unique name
        self.arrays = {}
        #: List of all dynamic arrays
        #: Dictionary mapping `DynamicArrayVariable` objects with 1 dimension to
        #: their globally unique name
        self.dynamic_arrays = {}
        #: Dictionary mapping `DynamicArrayVariable` objects with 2 dimensions
        #: to their globally unique name
        self.dynamic_arrays_2d = {}
        #: List of all arrays to be filled with zeros
        self.zero_arrays = []
        #: Dictionary of all arrays to be filled with numbers (mapping
        #: `ArrayVariable` objects to start value)
        self.arange_arrays = {}

        #: Whether the simulation has been run
        self.has_been_run = False

        #: Dict of all static saved arrays
        self.static_arrays = {}

        self.code_objects = {}
        self.main_queue = []
        self.report_func = ''
        self.synapses = []
        
        #: List of all source and header files (to be included in runner)
        self.source_files= []
        self.header_files= []

        self.clocks = set([])
        
    def reinit(self):
        self.__init__()

    def static_array(self, name, arr):
        assert len(arr), 'length for %s: %d' % (name, len(arr))
        name = '_static_array_' + name
        basename = name
        i = 0
        while name in self.static_arrays:
            i += 1
            name = basename+'_'+str(i)
        self.static_arrays[name] = arr.copy()
        return name

    def get_array_name(self, var, access_data=True):
        '''
        Return a globally unique name for `var`.

        Parameters
        ----------
        access_data : bool, optional
            For `DynamicArrayVariable` objects, specifying `True` here means the
            name for the underlying data is returned. If specifying `False`,
            the name of object itself is returned (e.g. to allow resizing).
        '''
        if isinstance(var, DynamicArrayVariable):
            if access_data:
                return self.arrays[var]
            elif var.dimensions == 1:
                return self.dynamic_arrays[var]
            else:
                return self.dynamic_arrays_2d[var]
        elif isinstance(var, ArrayVariable):
            return self.arrays[var]
        else:
            raise TypeError(('Do not have a name for variable of type '
                             '%s') % type(var))

    def add_array(self, var):
        # Note that a dynamic array variable is added to both the arrays and
        # the _dynamic_array dictionary
        if isinstance(var, DynamicArrayVariable):
            # The code below is slightly more complicated than just looking
            # for a unique name as above for static_array, the name has
            # potentially to be unique for more than one dictionary, with
            # different prefixes. This is because dynamic arrays are added to
            # a ``dynamic_arrays`` dictionary (with a `_dynamic` prefix) and to
            # the general ``arrays`` dictionary. We want to make sure that we
            # use the same name in the two dictionaries, not for example
            # ``_dynamic_array_source_name_2`` and ``_array_source_name_1``
            # (this would work fine, but it would make the code harder to read).
            orig_dynamic_name = dynamic_name = '_dynamic_array_%s_%s' % (var.owner.name, var.name)
            orig_array_name = array_name = '_array_%s_%s' % (var.owner.name, var.name)
            suffix = 0

            if var.dimensions == 1:
                dynamic_dict = self.dynamic_arrays
            elif var.dimensions == 2:
                dynamic_dict = self.dynamic_arrays_2d
            else:
                raise AssertionError(('Did not expect a dynamic array with %d '
                                      'dimensions.') % var.dimensions)
            while (dynamic_name in dynamic_dict.values() or
                   array_name in self.arrays.values()):
                suffix += 1
                dynamic_name = orig_dynamic_name + '_%d' % suffix
                array_name = orig_array_name + '_%d' % suffix
            dynamic_dict[var] = dynamic_name
            self.arrays[var] = array_name
        else:
            orig_array_name = array_name = '_array_%s_%s' % (var.owner.name, var.name)
            suffix = 0
            while (array_name in self.arrays.values()):
                suffix += 1
                array_name = orig_array_name + '_%d' % suffix
            self.arrays[var] = array_name


    def init_with_zeros(self, var):
        self.zero_arrays.append(var)

    def init_with_arange(self, var, start):
        self.arange_arrays[var] = start

    def init_with_array(self, var, arr):
        array_name = self.get_array_name(var, access_data=False)
        # treat the array as a static array
        self.static_arrays[array_name] = arr.astype(var.dtype)

    def fill_with_array(self, var, arr):
        arr = np.asarray(arr)
        if arr.shape == ():
            arr = np.repeat(arr, var.size)
        # Using the std::vector instead of a pointer to the underlying
        # data for dynamic arrays is fast enough here and it saves us some
        # additional work to set up the pointer
        array_name = self.get_array_name(var, access_data=False)
        static_array_name = self.static_array(array_name, arr)
        self.main_queue.append(('set_by_array', (array_name,
                                                 static_array_name)))
    def get_value(self, var, access_data=True):
        # Usually, we cannot retrieve the values of state variables in
        # standalone scripts since their values might depend on the evaluation
        # of expressions at runtime. For constant, read-only arrays that have
        # been explicitly initialized (static arrays) or aranges (e.g. the
        # neuronal indices) we can, however
        array_name = self.get_array_name(var, access_data=False)
        if (var.constant and var.read_only and
                (array_name in self.static_arrays or
                 var in self.arange_arrays)):
            if array_name in self.static_arrays:
                return self.static_arrays[array_name]
            elif var in self.arange_arrays:
                return np.arange(0, var.size) + self.arange_arrays[var]
        else:
            # After the network has been run, we can retrieve the values from
            # disk
            if self.has_been_run:
                dtype = var.dtype
                fname = os.path.join(self.project_dir, 'results',
                                     array_name)
                with open(fname, 'rb') as f:
                    data = np.fromfile(f, dtype=dtype)
                # This is a bit of an heuristic, but our 2d dynamic arrays are
                # only expanding in one dimension, we assume here that the
                # other dimension has size 0 at the beginning
                if isinstance(var.size, tuple) and len(var.size) == 2:
                    if var.size[0] * var.size[1] == len(data):
                        return data.reshape(var.size)
                    elif var.size[0] == 0:
                        return data.reshape((-1, var.size[1]))
                    elif var.size[0] == 0:
                        return data.reshape((var.size[1], -1))
                    else:
                        raise IndexError(('Do not now how to deal with 2d '
                                          'array of size %s, the array on disk '
                                          'has length %d') % (str(var.size),
                                                              len(data)))

                return data
            raise NotImplementedError('Cannot retrieve the values of state '
                                      'variables in standalone code before the '
                                      'simulation has been run.')

    def variableview_get_subexpression_with_index_array(self, variableview,
                                                        item, level=0,
                                                        run_namespace=None):
        raise NotImplementedError(('Cannot evaluate subexpressions in '
                                   'standalone scripts.'))


    def variableview_get_with_expression(self, variableview, code, level=0,
                                         run_namespace=None):
        raise NotImplementedError('Cannot retrieve the values of state '
                                  'variables with string expressions in '
                                  'standalone scripts.')

    def code_object_class(self, codeobj_class=None):
        if codeobj_class is GeNNCodeObject:
            return codeobj_class
        else:
            return GeNNUserCodeObject

    def code_object(self, owner, name, abstract_code, variables, template_name,
                    variable_indices, codeobj_class=None, template_kwds=None,
                    override_conditional_write=None):
        if template_name in [ 'summed_variable', 'ratemonitor' ]:
            raise NotImplementedError('The function of %s is not yet supported in GeNN.'%template_name)
        if template_name in [ 'stateupdate', 'threshold', 'reset', 'synapses' ]:
            codeobj_class= GeNNCodeObject
        else:
            codeobj_class= GeNNUserCodeObject
        codeobj = super(GeNNDevice, self).code_object(owner, name, abstract_code, variables,
                                                      template_name, variable_indices,
                                                      codeobj_class=codeobj_class,
                                                      template_kwds=template_kwds,
                                                      override_conditional_write=override_conditional_write,
        )
        self.code_objects[codeobj.name] = codeobj
        return codeobj
        

    #---------------------------------------------------------------------------------
    def make_main_lines(self):
        main_lines = []
        procedures = [('', main_lines)]
        runfuncs = {}
        for func, args in self.main_queue:
            if func=='run_code_object':
                codeobj, = args
                # a bit of a hack to explicitly exclude spike queue related code objects here: TODO
                if ('initialise_queue' not in codeobj.name) and ('push_spikes' not in codeobj.name): 
                    main_lines.append('_run_%s();' % codeobj.name)
            elif func=='run_network':
                 net, netcode = args
                 #                 main_lines.extend(netcode)
            elif func=='set_by_array':
                arrayname, staticarrayname = args
                code = '''
                for(int i=0; i<_num_{staticarrayname}; i++)
                {{
                    {arrayname}[i] = {staticarrayname}[i];
                }}
                '''.format(arrayname=arrayname, staticarrayname=staticarrayname)
                main_lines.extend(code.split('\n'))
            elif func=='set_array_by_array':
                arrayname, staticarrayname_index, staticarrayname_value = args
                code = '''
                for(int i=0; i<_num_{staticarrayname_index}; i++)
                {{
                    {arrayname}[{staticarrayname_index}[i]] = {staticarrayname_value}[i];
                }}
                '''.format(arrayname=arrayname, staticarrayname_index=staticarrayname_index,
                           staticarrayname_value=staticarrayname_value)
                main_lines.extend(code.split('\n'))
            elif func=='insert_code':
                main_lines.append(args)
            elif func=='start_run_func':
                name, include_in_parent = args
                if include_in_parent:
                    main_lines.append('%s();' % name)
                main_lines = []
                procedures.append((name, main_lines))
            elif func=='end_run_func':
                name, include_in_parent = args
                name, main_lines = procedures.pop(-1)
                runfuncs[name] = main_lines
                name, main_lines = procedures[-1]
            else:
                raise NotImplementedError("Unknown main queue function type "+func)
                
        # generate the finalisations
        for codeobj in self.code_objects.itervalues():
            if hasattr(codeobj.code, 'main_finalise'):
                main_lines.append(codeobj.code.main_finalise)
        return main_lines

    #---------------------------------------------------------------------------------
    def build(self, directory='output', compile=True, run=True, use_GPU=True):
        '''
        TODO: comments here
        '''

        # Check for GeNN compatibility
#        if len(self.dynamic_arrays) or len(self.dynamic_arrays_2d):
#            raise NotImplementedError("GeNN does not support objects that use dynamic arrays (Synapses, SpikeMonitor, etc.)")
                

        # Start building the project

        self.project_dir = directory
        ensure_directory(directory)
        for d in ['code_objects', 'results', 'static_arrays']:
            ensure_directory(os.path.join(directory, d))

        writer = CPPWriter(directory)

        logger.debug("Writing GeNN project to directory "+os.path.normpath(directory))

# DO WE NEED TO WORRY ABOUT THESE? ARE THERE USER-DEFINED ONES IN THERE?
        arange_arrays = sorted([(var, start)
                                for var, start in self.arange_arrays.iteritems()],
                               key=lambda (var, start): var.name)
        
        #arange_arrays = []
        
        # write the static arrays
        logger.debug("static arrays: "+str(sorted(self.static_arrays.keys())))
        static_array_specs = []
        for name, arr in sorted(self.static_arrays.items()):
            arr.tofile(os.path.join(directory, 'static_arrays', name))
            static_array_specs.append((name, c_data_type(arr.dtype), arr.size, name))
        
        networks = [net() for net in Network.__instances__() if net().name!='_fake_network']
        synapses = []
        for net in networks:
            synapses.extend(s for s in net.objects if isinstance(s, Synapses))
        
#        if len(synapses):
#            raise NotImplementedError("GeNN does not support Synapses (yet).")
        
        if len(networks)!=1:
            raise NotImplementedError("GeNN only supports MagicNetwork")
        net = networks[0]

        # Not sure what the best place is to call Network.after_run -- at the
        # moment the only important thing it does is to clear the objects stored
        # in magic_network. If this is not done, this might lead to problems
        # for repeated runs of standalone (e.g. in the test suite).
        # for net in networks:
        #     net.after_run()

        arr_tmp = GeNNUserCodeObject.templater.objects(
                        None, None,
                        array_specs=self.arrays,
                        dynamic_array_specs=self.dynamic_arrays,
                        dynamic_array_2d_specs=self.dynamic_arrays_2d,
                        zero_arrays=self.zero_arrays,
                        arange_arrays=arange_arrays,
                        synapses=synapses,
                        clocks=self.clocks,
                        static_array_specs=static_array_specs,
                        networks= [net],
                        )
        writer.write('objects.*', arr_tmp)
        self.header_files.append('objects.h')
        self.source_files.append('objects.cpp')

        main_lines = self.make_main_lines()

        # Generate data for non-constant values
        code_object_defs = defaultdict(list)
        for codeobj in self.code_objects.itervalues():
            print(codeobj.name)
            lines = []
            for k, v in codeobj.variables.iteritems():
                if isinstance(v, AttributeVariable):
                    # We assume all attributes are implemented as property-like methods
                    line = 'const {c_type} {varname} = {objname}.{attrname}();'
                    lines.append(line.format(c_type=c_data_type(v.dtype), varname=k, objname=v.obj.name,
                                             attrname=v.attribute))
                elif isinstance(v, ArrayVariable):
                    try:
                        if isinstance(v, DynamicArrayVariable):
                            if v.dimensions == 1:
                                dyn_array_name = self.dynamic_arrays[v]
                                array_name = self.arrays[v]
                                line = '{c_type}* const {array_name} = &{dyn_array_name}[0];'
                                line = line.format(c_type=c_data_type(v.dtype), array_name=array_name,
                                                   dyn_array_name=dyn_array_name)
                                lines.append(line)
                                line = 'const int _num{k} = {dyn_array_name}.size();'
                                line = line.format(k=k, dyn_array_name=dyn_array_name)
                                lines.append(line)
                        else:
                            lines.append('const int _num%s = %s;' % (k, v.size))
                    except TypeError:
                        pass
            for line in lines:
                # Sometimes an array is referred to by to different keys in our
                # dictionary -- make sure to never add a line twice
                if not line in code_object_defs[codeobj.name]:
                    code_object_defs[codeobj.name].append(line)
        # Generate the code objects
        for codeobj in self.code_objects.itervalues():
            ns = codeobj.variables
            # TODO: fix these freeze/CONSTANTS hacks somehow - they work but not elegant.
            # print(type(codeobj.code))
            if isinstance(codeobj.code, MultiTemplate):
                code = freeze(codeobj.code.cpp_file, ns)
                code = code.replace('%CONSTANTS%', '\n'.join(code_object_defs[codeobj.name]))
                code = '#include "objects.h"\n'+code
            
                writer.write('code_objects/'+codeobj.name+'.cpp', code)
                self.source_files.append('code_objects/'+codeobj.name+'.cpp')
                writer.write('code_objects/'+codeobj.name+'.h', codeobj.code.h_file)
                self.header_files.append('code_objects/'+codeobj.name+'.h')
                

        # assemble the model descriptions:
        objects = dict((obj.name, obj) for obj in net.objects)
        neuron_groups = [obj for obj in net.objects if isinstance(obj, NeuronGroup)]
        synapse_groups=[ obj for obj in net.objects if isinstance(obj, Synapses)]
        spike_monitors= [ obj for obj in net.objects if isinstance(obj, SpikeMonitor)]
        state_monitors= [ obj for obj in net.objects if isinstance(obj, StateMonitor)]
        self.model_name= net.name+'_model'
        self.dtDef= '#define DT '+ repr(float(defaultclock.dt))
        for obj in neuron_groups:
            # Extract the variables
            neuron_model= neuronModel()
            neuron_model.name= obj.name
            neuron_model.N= obj.N
            for k, v in obj.variables.iteritems():
                if k == '_spikespace' or k == 't' or k == 'dt':
                    pass
                elif isinstance(v, ArrayVariable):
                    neuron_model.variables.append(k)
                    neuron_model.variabletypes.append(c_data_type(v.dtype))
   
            for suffix, lines in [('_stateupdater', neuron_model.code_lines),
                                  ('_thresholder', neuron_model.thresh_cond_lines),
                                  ('_resetter', neuron_model.reset_code_lines),
                                  ]:
                if obj.name+suffix not in objects:
                    if suffix == '_thresholder':
                        lines.append('0')
                    continue
                        
                codeobj = objects[obj.name+suffix].codeobj
                for k, v in codeobj.variables.iteritems():
                    if k != 'dt' and isinstance(v, Constant):
                        if k not in neuron_model.parameters:
                            neuron_model.parameters.append(k)
                            neuron_model.pvalue.append(repr(v.value)) 
                   
                print('The code is:')
                print(codeobj.code)
                code = decorate(codeobj.code, neuron_model.variables, neuron_model.parameters).strip()
                lines.append(code)                    
            
            self.neuron_models.append(neuron_model)

#        for obj in objects:
#            print(type(obj), obj)
        for obj in synapse_groups:
            synapse_model= synapseModel()
            synapse_model.name= obj.name
            synapse_model.srcname= obj.source.name
            synapse_model.srcN= obj.source._N
            synapse_model.trgname= obj.target.name
            synapse_model.trgN= obj.target._N

            if hasattr(obj, 'pre'):
                codeobj= obj.pre.codeobj
                for k, v in codeobj.variables.iteritems():
                    if k == '_spikespace' or k == 't' or k == 'dt' :
                        pass
                    elif isinstance(v, Constant):
                        if k not in synapse_model.parameters:
                            synapse_model.parameters.append(k)
                            synapse_model.pvalue.append(repr(v.value))
                    elif isinstance(v, ArrayVariable):
                        if k in codeobj.code.__str__():
                            if '_pre' not in k and '_post' not in k:
                                if k not in synapse_model.variables:
                                    print('appending ', k)
                                    print synapse_model.variables
                                    if codeobj.variable_indices[k] == '_idx':
                                        synapse_model.variables.append(k)
                                        synapse_model.variabletypes.append(c_data_type(v.dtype))
                            else:
                                if k not in synapse_model.external_variables:
                                    synapse_model.external_variables.append(k)
                code= codeobj.code
                code_lines = [line.strip() for line in code.split('\n')]
                new_code_lines = []
                for line in code_lines:
                    new_code_lines.append(line)
                    if line.startswith('addtoinSyn'):
                        new_code_lines.append('$(updatelinsyn);')
                code = '\n'.join(new_code_lines)
                code= 'if (_hidden_weightmatrix != 0.0) {'+code+'}'
                thecode = decorate(code, synapse_model.variables, synapse_model.parameters, False).strip()
                thecode = decorate(thecode, synapse_model.external_variables, [], True).strip()
                synapse_model.simCode= thecode

            if hasattr(obj, 'post'):
                codeobj= obj.post.codeobj
                code= codeobj.code
                for k, v in codeobj.variables.iteritems():
                    if k == '_spikespace' or k == 't' or k == 'dt' :
                        pass
                    elif isinstance(v, Constant):
                        if k not in synapse_model.parameters:
                            synapse_model.parameters.append(k)
                            synapse_model.pvalue.append(repr(v.value))
                    elif isinstance(v, ArrayVariable):
                        if k in codeobj.code.__str__():
                            if '_pre' not in k and '_post' not in k:
                                if k not in synapse_model.variables:
                                    print('synapse post appending ', k)
                                    #                                if codeobj.indices[k] == '_idx':
                                    synapse_model.variables.append(k)
                                    synapse_model.variabletypes.append(c_data_type(v.dtype))
                                    print synapse_model.variables
                                
                            else:
                                if k not in synapse_model.external_variables:
                                    synapse_model.external_variables.append(k)
                code= 'if (_hidden_weightmatrix != 0.0) {'+code+'}'
                thecode = decorate(code, synapse_model.variables, synapse_model.parameters, False).strip()
                thecode = decorate(thecode, synapse_model.postsyn_variables, synapse_model.postsyn_parameters, False).strip()
                thecode = decorate(thecode, synapse_model.external_variables, [], True).strip()
                synapse_model.simLearnPost= thecode  

            
            if obj.state_updater != None:
                codeobj= obj.state_updater.codeobj
                code= codeobj.code
                for k, v in codeobj.variables.iteritems():
                    if k == '_spikespace' or k == 't' or k == 'dt' :
                        pass
                    elif isinstance(v, Constant):
                        if k not in synapse_model.parameters:
                            synapse_model.parameters.append(k)
                            synapse_model.pvalue.append(repr(v.value))
                    elif isinstance(v, ArrayVariable):
                        if k in codeobj.code.__str__():
                            if '_pre' not in k and '_post' not in k:
                                if k not in synapse_model.variables:
                                    print('appending ', k)
                                    #                               if codeobj.indices[k] == '_idx':
                                    synapse_model.variables.append(k)
                                    synapse_model.variabletypes.append(c_data_type(v.dtype))
                                    print synapse_model.variables
                            else:
                                if k not in synapse_model.external_variables:
                                    synapse_model.external_variables.append(k) 
                code= 'if (_hidden_weightmatrix != 0.0) {'+code+'}'
                thecode = decorate(code, synapse_model.variables, synapse_model.parameters, False).strip()
                thecode = decorate(thecode, synapse_model.postsyn_variables, synapse_model.postsyn_parameters, False).strip()               
                thecode = decorate(thecode, synapse_model.external_variables, [], True).strip()
                synapse_model.synapseDynamics= thecode  
                
            if (hasattr(obj,'_genn_post_write_var')):
                synapse_model.postSyntoCurrent= '0; $(' + obj._genn_post_write_var.replace('_post','') + ') += $(inSyn); $(inSyn)= 0'
            else:
                synapse_model.postSyntoCurrent= '0'
            self.synapse_models.append(synapse_model)
                               
        for obj in spike_monitors:
            sm= spikeMonitorModel()
            sm.name= obj.name
            sm.neuronGroup= obj.source.name
            print sm.name
            print sm.neuronGroup
            self.spike_monitor_models.append(sm)
            self.header_files.append('code_objects/'+sm.name+'_codeobject.h')
            
        for obj in state_monitors:
            sm= stateMonitorModel()
            sm.name= obj.name
            sm.neuronGroup= obj.source.name
            print sm.name
            print sm.neuronGroup
            self.state_monitor_models.append(sm)
            self.header_files.append('code_objects/'+sm.name+'_codeobject.h')

        print len(self.spike_monitor_models)
        # Copy the brianlib directory
        brianlib_dir = os.path.join(os.path.split(inspect.getsourcefile(CPPStandaloneCodeObject))[0],
                                    'brianlib')
        brianlib_files = copy_directory(brianlib_dir, os.path.join(directory, 'brianlib'))
        for file in brianlib_files:
            if file.lower().endswith('.cpp'):
                self.source_files.append('brianlib/'+file)
            elif file.lower().endswith('.h'):
                self.header_files.append('brianlib/'+file)

        # Copy the CSpikeQueue implementation
        spikequeue_h = os.path.join(directory, 'brianlib', 'spikequeue.h')
        shutil.copy2(os.path.join(os.path.split(inspect.getsourcefile(Synapses))[0], 'cspikequeue.cpp'),
                     spikequeue_h)
        

        # Copy the b2glib directory
        b2glib_dir = os.path.join(os.path.split(inspect.getsourcefile(GeNNCodeObject))[0],
                                    'b2glib')
        b2glib_files = copy_directory(b2glib_dir, os.path.join(directory, 'b2glib'))
        for file in b2glib_files:
            if file.lower().endswith('.cc'):
                self.source_files.append('b2glib/'+file)
            elif file.lower().endswith('.h'):
                self.header_files.append('b2glib/'+file)
        
        synapses_classes_tmp = CPPStandaloneCodeObject.templater.synapses_classes(None, None)
        writer.write('synapses_classes.*', synapses_classes_tmp)

        model_tmp = GeNNCodeObject.templater.model(None, None,
                                                   neuron_models= self.neuron_models,
                                                   synapse_models= self.synapse_models,
                                                   dtDef= self.dtDef,
                                                   model_name= self.model_name,
                                                   )
        open(os.path.join(directory,self.model_name+'.cc'), 'w').write(model_tmp)

        runner_tmp = GeNNCodeObject.templater.runner(None, None,
                                                     neuron_models= self.neuron_models,
                                                     synapse_models= self.synapse_models,
                                                     model_name= self.model_name,
                                                     main_lines= main_lines,
                                                     header_files= self.header_files,
                                                     source_files= self.source_files,
                                                     )        
        open(os.path.join(directory, 'runner.cu'), 'w').write(runner_tmp.cpp_file)
        open(os.path.join(directory, 'runner.h'), 'w').write(runner_tmp.h_file)
        engine_tmp = GeNNCodeObject.templater.engine(None, None,
                                                     neuron_models= self.neuron_models,
                                                     synapse_models= self.synapse_models,
spike_monitor_models= self.spike_monitor_models,
state_monitor_models= self.state_monitor_models,
                                                     model_name= self.model_name,
                                                     )        
        open(os.path.join(directory, 'engine.cc'), 'w').write(engine_tmp.cpp_file)
        open(os.path.join(directory, 'engine.h'), 'w').write(engine_tmp.h_file)

        if os.sys.platform == 'win32':
            Makefile_tmp= GeNNCodeObject.templater.WINmakefile(None, None,
                                                        neuron_models= self.neuron_models,
                                                        model_name= self.model_name,
                                                        ROOTDIR= os.path.abspath(directory),
                                                        source_files= self.source_files,
                                                        ) 
            open(os.path.join(directory, 'WINmakefile'), 'w').write(Makefile_tmp)
        else:
            Makefile_tmp= GeNNCodeObject.templater.GNUmakefile(None, None,
                                                        neuron_models= self.neuron_models,
                                                        model_name= self.model_name,
                                                        ROOTDIR= os.path.abspath(directory),
                                                        source_files= self.source_files,
                                                        ) 
            open(os.path.join(directory, 'GNUmakefile'), 'w').write(Makefile_tmp)

        if compile:
            if os.sys.platform == 'win32':
                bitversion= ''
                if os.getenv('PROCESSOR_ARCHITECTURE') == "AMD64":
                    bitversion= 'x86_amd64'
                elif os.getenv('PROCESSOR_ARCHITEW6432') == "AMD64":
                    bitversion= 'x86_amd64'
                else:
                    bitversion= 'x86'

                # Users are required to set their path to "Visual Studio/VC", e.g.
                # setx VS_PATH "C:\Program Files (x86)\Microsoft Visual Studio 10.0"
                cmd= "\""+os.getenv('VS_PATH')+"\\VC\\vcvarsall.bat\" " + bitversion
                print(cmd)
                cmd= cmd+" && buildmodel.bat "+self.model_name + " && nmake /f WINmakefile clean && nmake /f WINmakefile"
                call(cmd, cwd=directory)
            else:
                call(["buildmodel.sh", self.model_name], cwd=directory)
                call(["make", "clean"], cwd=directory)
                call(["make"], cwd=directory)

        if run:
            gpu_arg = "1" if use_GPU else "0"
            if  os.sys.platform == 'win32':
                print directory
                cmd= directory + "\\runner.exe test " + str(self.run_duration) + " " + gpu_arg
                print cmd
                #os.system(cmd)
                call(cmd, cwd=directory)
            else:
                print directory
                print ["./runner", "test", str(self.run_duration), gpu_arg]
                call(["./runner", "test", str(self.run_duration), gpu_arg], cwd=directory)
            self.has_been_run= True

    def network_run(self, net, duration, report=None, report_period=10*second,
                    namespace=None, level=0, **kwds):
        if kwds:
            logger.warn(('Unsupported keyword argument(s) provided for run: '
+ '%s') % ', '.join(kwds.keys()))
            
        if self.run_duration is not None:
            raise NotImplementedError('Only a single run statement is supported.')
        self.run_duration = float(duration)
        super(GeNNDevice, self).network_run(net= net, duration= duration, report=report, report_period=report_period, namespace=namespace, level=level+1)


genn_device = GeNNDevice()

all_devices['genn'] = genn_device

