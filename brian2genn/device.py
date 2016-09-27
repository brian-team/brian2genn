'''
Module implementing the bulk of the brian2genn interface by defining the "genn" device.
'''

import os
from subprocess import call
import inspect
from collections import defaultdict
import tempfile
import numpy
import numbers
import time

from brian2.spatialneuron.spatialneuron import SpatialNeuron, SpatialStateUpdater
from brian2.units import second
from brian2.codegen.generators.cpp_generator import c_data_type
from brian2.codegen.templates import MultiTemplate
from brian2.core.clocks import defaultclock
from brian2.core.variables import *
from brian2.core.network import Network
from brian2.devices.device import all_devices
from brian2.devices.cpp_standalone.device import CPPStandaloneDevice
from brian2.parsing.rendering import CPPNodeRenderer
from brian2.synapses.synapses import Synapses, SynapticPathway
from brian2.monitors.spikemonitor import SpikeMonitor
from brian2.monitors.ratemonitor import PopulationRateMonitor
from brian2.monitors.statemonitor import StateMonitor
from brian2.utils.filetools import copy_directory, ensure_directory
from brian2.utils.stringtools import word_substitute, get_identifiers
from brian2.groups.group import Group
from brian2.groups.neurongroup import NeuronGroup, StateUpdater, Resetter, Thresholder
from brian2.groups.subgroup import Subgroup
from brian2.input.poissongroup import PoissonGroup
from brian2.input.spikegeneratorgroup import *
from brian2.synapses.synapses import StateUpdater as SynapsesStateUpdater
from brian2.utils.logger import get_logger, std_silent
from brian2.devices.cpp_standalone.codeobject import CPPStandaloneCodeObject
from brian2.devices.cpp_standalone.device import CPPWriter
from brian2 import prefs
from .codeobject import GeNNCodeObject, GeNNUserCodeObject


__all__ = ['GeNNDevice']

logger = get_logger('brian2.devices.genn')
prefs['codegen.generators.cpp.restrict_keyword']= '__restrict'
prefs['codegen.loop_invariant_optimisations'] = False
prefs['core.network.default_schedule']= ['start', 'synapses', 'groups', 'thresholds', 'resets', 'end']


def stringify(code):
    '''
    Helper function to prepare multiline strings (potentially including
    quotation marks) to be included in strings.

    Examples
    --------
    >>> print(stringify('v = 0*mV;\nv_th += 3*mV;'))
    v = 0*mV;\n\
    v_th += 3*mV;
    >>> print(stringify('name = "foo";'))
    name = \"foo\";
    '''
    code = code.replace('\n', '\\n\\\n')
    code = code.replace('"', '\\"')
    return code


def freeze(code, ns):
    '''
    Support function for substituting constant values.
    ''' 
    # this is a bit of a hack, it should be passed to the template somehow
    for k, v in ns.items():

        if (isinstance(v, Variable) and 
              v.scalar and v.constant and v.read_only):
            try:
                v = v.get_value()
            except NotImplementedError:
                continue
        if isinstance(v, basestring):
            code = word_substitute(code, {k: v})
        elif isinstance(v, numbers.Number):
            # Use a renderer to correctly transform constants such as True or inf
            renderer = CPPNodeRenderer()
            string_value = renderer.render_expr(repr(v))
            if v < 0:
                string_value = '(%s)' % string_value
            code = word_substitute(code, {k: string_value})
        else:
            pass  # don't deal with this object
    return code


def decorate(code, variables, parameters, do_final= True):
    '''
    Support function for inserting GeNN-specific "decorations" for variables and parameters, such as $(.).
    '''
    # this is a bit of a hack, it should be part of the language probably
    for v in variables:
        code = word_substitute(code, {v : '$('+v+')'})
    for p in parameters:
        code = word_substitute(code, {p : '$('+p+')'})
    code = word_substitute(code, {'dt' : 'DT'}).strip()
    if do_final: 
        code = stringify(code)
        code = word_substitute(code, {'addtoinSyn' : '$(addtoinSyn)'})
        code = word_substitute(code, {'_hidden_weightmatrix' : '$(_hidden_weightmatrix)'})
    return code


def extract_source_variables(variables, varname, smvariables):
    '''Support function to extract the "atomic" variables used in a variable that is of instance `Subexpression`.
    '''
    identifiers= get_identifiers(variables[varname].expr)
    for vnm, var in variables.items():
        if vnm in identifiers:
            if isinstance(var,ArrayVariable):
                smvariables.append(vnm)
            elif isinstance(var,Subexpression):
                smvariables= extract_source_variables(variables, vnm, smvariables)
    return smvariables


class neuronModel(object):
    '''
    Class that contains all relevant information of a neuron model. 
    '''
    def __init__(self):
        self.name=''
        self.N= 0
        self.variables= []
        self.variabletypes= []
        self.variablescope= dict()
        self.parameters= []
        self.pvalue= []
        self.code_lines= []
        self.thresh_cond_lines= []
        self.reset_code_lines= []
        self.support_code_lines= []

class spikegeneratorModel(object):
    '''
    Class that contains all relevant information of a spike generator group.
    '''
    def __init__(self):
        self.name=''
        self.N= 0


class synapseModel(object):
    '''
    Class that contains all relevant information about a synapse model.
    '''
    def __init__(self):
        self.name = ''
        self.srcname = ''
        self.srcN = 0
        self.trgname = ''
        self.trgN = 0
        self.N = 0
        self.variables = []
        self.variabletypes = []
        self.variablescope = dict()
        self.external_variables = []
        self.parameters = []
        self.pvalue = []
        self.postSyntoCurrent = []
        # The following dictionaries contain keys "pre"/"post" for the pre-
        # and post-synaptic pathway and "dynamics" for the synaptic dynamics
        self.main_code_lines = defaultdict(str)
        self.support_code_lines = defaultdict(str)
        self.connectivity = ''
        self.delay = 0


class spikeMonitorModel(object):
    '''
    Class the contains all relevant information about a spike monitor.
    '''
    def __init__(self):
        self.name=''
        self.neuronGroup=''
        self.notSpikeGeneratorGroup= True


class rateMonitorModel(object):
    '''
    CLass that contains all relevant information about a rate monitor.
    '''
    def __init__(self):
        self.name=''
        self.neuronGroup=''
        self.notSpikeGeneratorGroup= True


class stateMonitorModel(object):
    '''
    Class that contains all relvant information about a state monitor.
    '''
    def __init__(self):
        self.name=''
        self.monitored=''
        self.isSynaptic= False
        self.variables= []
        self.srcN= 0
        self.trgN= 0
        self.when=''
        self.connectivity=''

class CPPWriter(object):
    '''
    Class that provides the method for writing C++ files from a string of code.
    '''
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

#-----------------------------------------------------------------------------------------------------------
# Start of GeNNDevice
#-----------------------------------------------------------------------------------------------------------

class GeNNDevice(CPPStandaloneDevice):
    '''
    The main "genn" device. This does most of the translation work from Brian 2 generated code to functional GeNN code, assisted by the "GeNN language".
    '''
    def __init__(self):
        super(GeNNDevice, self).__init__()   
        self.network_schedule= ['start', 'synapses', 'groups', 'thresholds', 'resets', 'end']
        self.neuron_models = []
        self.spikegenerator_models= []
        self.synapse_models = []
        self.delays = {}
        self.spike_monitor_models= []
        self.rate_monitor_models= []
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
        self.simple_code_objects = {}
        self.main_queue = []
        self.report_func = ''
        self.synapses = []
        
        #: List of all source and header files (to be included in runner)
        self.source_files= []
        self.header_files= []

        self.clocks = set([])
        self.connectivityDict = dict()
        self.groupDict= dict()

    def activate(self, build_on_run, **kwargs):
        prefs.codegen.loop_invariant_optimisations = False
        prefs._backup()
        super(GeNNDevice, self).activate(build_on_run, **kwargs)

    def code_object_class(self, codeobj_class=None):
        if codeobj_class is GeNNCodeObject:
            return codeobj_class
        else:
            return GeNNUserCodeObject

    def code_object(self, owner, name, abstract_code, variables, template_name,
                    variable_indices, codeobj_class=None, template_kwds=None,
                    override_conditional_write=None):
        '''
        Processes abstract code into code objects and stores them in different arrays for `GeNNCodeObjects` and `GeNNUserCodeObjects`.
        '''
        if template_name in [ 'stateupdate', 'threshold', 'reset', 'synapses' ]:
            codeobj_class= GeNNCodeObject
            codeobj = super(GeNNDevice, self).code_object(owner, name, abstract_code, variables,
                                                          template_name, variable_indices,
                                                          codeobj_class=codeobj_class,
                                                          template_kwds=template_kwds,
                                                          override_conditional_write=override_conditional_write,
                                                      )
            self.simple_code_objects[codeobj.name] = codeobj
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

    # The following two methods are only overwritten to catch assignments to the
    # delay variable -- GeNN does not support heterogeneous delays
    def fill_with_array(self, var, arr):
        if isinstance(var.owner, Synapses) and var.name == 'delay':
            # Assigning is only allowed if the variable has been declared in the
            # Synapse constructor and is therefore scalar
            if not var.scalar:
                raise NotImplementedError('GeNN does not support assigning to the '
                                          'delay variable -- set the delay for all'
                                          'synapses (heterogeneous delays are not '
                                          'supported) as an argument to the '
                                          'Synapses initializer.')
            else:
                # We store the delay so that we can later access it
                self.delays[var.owner.name] = numpy.asarray(arr).item()
        super(GeNNDevice, self).fill_with_array(var, arr)

    def variableview_set_with_index_array(self, variableview, item,
                                          value, check_units):
        var = variableview.variable
        if isinstance(var.owner, Synapses) and var.name == 'delay':
            raise NotImplementedError('GeNN does not support assigning to the '
                                      'delay variable -- set the delay for all'
                                      'synapses (heterogeneous delays are not '
                                      'supported) as an argument to the '
                                      'Synapses initializer.')
        super(GeNNDevice, self).variableview_set_with_index_array(variableview,
                                                                  item,
                                                                  value,
                                                                  check_units)

    #---------------------------------------------------------------------------------
    def make_main_lines(self):
        '''
        Generates the code lines that handle initialisation of Brian 2 cpp_standalone type arrays. These are then translated into the appropriate GeNN data structures in separately generated code.
        '''
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
                 # do nothing
            elif func=='set_by_constant':
                arrayname, value, is_dynamic = args
                size_str = arrayname+'.size()' if is_dynamic else '_num_'+arrayname
                code = '''
                for(int i=0; i<{size_str}; i++)
                {{
                    {arrayname}[i] = {value};
                }}
                '''.format(arrayname=arrayname, size_str=size_str,
                           value=CPPNodeRenderer().render_expr(repr(value)))
                main_lines.extend(code.split('\n'))
            elif func=='set_by_array':
                arrayname, staticarrayname, is_dynamic = args
                size_str = arrayname+'.size()' if is_dynamic else '_num_'+arrayname
                code = '''
                for(int i=0; i<{size_str}; i++)
                {{
                    {arrayname}[i] = {staticarrayname}[i];
                }}
                '''.format(arrayname=arrayname, size_str=size_str,
                           staticarrayname=staticarrayname)
                main_lines.extend(code.split('\n'))
            elif func=='set_by_single_value':
                arrayname, item, value = args
                code = '{arrayname}[{item}] = {value};'.format(arrayname=arrayname,
                                                               item=item,
                                                               value=value)
                main_lines.extend([code])
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
            elif func=='resize_array':
                array_name, new_size = args
                main_lines.append("{array_name}.resize({new_size});".format(array_name=array_name,
                                                                            new_size=new_size))
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

    def fix_random_generators(self,model,code):
        '''
        Translates cpp_standalone style random number generator calls into GeNN compatible calls by replacing the cpp_standalone `_vectorisation_idx` argument with the GeNN `_seed` argument.
        '''
        for func in ['_rand', '_randn','_binomial','_binomial_1']:
            if func+'(_vectorisation_idx)' in code:
                code = code.replace(func+'(_vectorisation_idx)', func+'(_seed)')
                if not '_seed' in model.variables:
                    model.variables.append('_seed')
                    model.variabletypes.append('uint64_t')
                    model.variablescope['_seed']='genn'
        if '_brian_mod' in code:
            code= code.replace('_brian_mod','fmod')
            
        return code

    #---------------------------------------------------------------------------------
    def build(self, directory='GeNNworkspace', compile=True, run=True, use_GPU=True,
              debug=False, with_output=True, direct_call=True):
        '''
        This function does the main post-translation work for the genn device. It uses the code generated during/before run() and extracts information about neuron groups, synapse groups, monitors, etc. that is then formatted for use in GeNN-specific templates.
        The overarching strategy of the brian2genn interface is to use cpp_standalone code generation and templates for most of the "user-side code" (in the meaning defined in GeNN) and have GeNN specific templates for the model definition and the main code for the executable that pulls everything together (in main.cpp and engine.cpp templates). The haqndling of input/output arrays for everything is lent from cpp_standalone and the cpp_standalone arrays are then translated into GeNN-suitable data structures using the static (not code-generated) b2glib library functions. This means that the GeNN specific cod only has to be concerned about execyting the correct model and feeding back results into the appropriate cpp_standlaone data structures.
        '''

        print 'building genn executable ...'
        # Check for GeNN compatibility

        if directory is None:  # used during testing
            directory = tempfile.mkdtemp()

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
        
        # write the static arrays
        logger.debug("static arrays: "+str(sorted(self.static_arrays.keys())))
        static_array_specs = []
        for name, arr in sorted(self.static_arrays.items()):
            arr.tofile(os.path.join(directory, 'static_arrays', name))
            static_array_specs.append((name, c_data_type(arr.dtype), arr.size, name))
        
        networks = [net() for net in Network.__instances__() if net().name!='_fake_network']
        
        if len(networks) != 1:
            raise NotImplementedError("GeNN only supports a single network")
        net = networks[0]

        synapses = []
        synapses.extend(s for s in net.objects if isinstance(s, Synapses))

        self.generate_objects_source(arange_arrays, net, static_array_specs,
                                     synapses, writer)

        main_lines = self.make_main_lines()

        self.generate_code_objects(writer)

        # assemble the model descriptions:
        objects = dict((obj.name, obj) for obj in net.objects)
        neuron_groups = [obj for obj in net.objects if isinstance(obj, NeuronGroup)]
        poisson_groups = [obj for obj in net.objects if isinstance(obj, PoissonGroup)]
        spikegenerator_groups = [obj for obj in net.objects if isinstance(obj, SpikeGeneratorGroup)]

        synapse_groups=[ obj for obj in net.objects if isinstance(obj, Synapses)]
        spike_monitors= [ obj for obj in net.objects if isinstance(obj, SpikeMonitor)]
        rate_monitors= [ obj for obj in net.objects if isinstance(obj, PopulationRateMonitor)]
        state_monitors= [ obj for obj in net.objects if isinstance(obj, StateMonitor)]
        for obj in net.objects:
            if isinstance(obj, (SpatialNeuron, SpatialStateUpdater)):
                raise NotImplementedError('Brian2GeNN does not support multicompartmental neurons')
            if not isinstance(obj, (NeuronGroup, PoissonGroup, SpikeGeneratorGroup, Synapses,
                                    SpikeMonitor, PopulationRateMonitor, StateMonitor,
                                    StateUpdater, SynapsesStateUpdater, Resetter,
                                    Thresholder, SynapticPathway)):
                raise NotImplementedError("Brian2GeNN does not support objects of type "
                                          "'%s'" % str(obj.__class__.__name__))
        self.model_name= net.name+'_model'
        self.dtDef= 'model.setDT('+ repr(float(defaultclock.dt))+');'

        # Process groups
        self.process_neuron_groups(neuron_groups, objects)
        self.process_poisson_groups(objects, poisson_groups)
        self.process_spikegenerators(spikegenerator_groups)
        self.process_synapses(synapse_groups)

        # Process monitors
        self.process_spike_monitors(spike_monitors)
        self.process_rate_monitors(rate_monitors)
        self.process_state_monitors(directory, state_monitors, writer)

        # Write files from templates
        self.copy_source_files(writer, directory)
        self.generate_model_source(writer)
        self.generate_main_source(writer, main_lines)
        self.generate_engine_source(writer)
        self.generate_makefile(directory, use_GPU)

        # Compile and run
        if compile:
            self.compile_source(debug, directory, use_GPU)
        if run:
            self.run(directory, use_GPU, with_output)

#------------------------------------------------------------------------------
# the network run function - needs to throw some errors for not-implemented features such as multiple clocks

    def generate_code_objects(self, writer):
        # Generate data for non-constant values
        code_object_defs = defaultdict(list)
        for codeobj in self.code_objects.itervalues():
            lines = []
            for k, v in codeobj.variables.iteritems():
                # if isinstance(v, AttributeVariable):
                #     # We assume all attributes are implemented as property-like methods
                #     line = 'const {c_type} {varname} = {objname}.{attrname}();'
                #     # HACK: Avoid over-shadowing the global variable 't' provided by GeNN - code should use GeNN's t anyway
                #     if (k != 't'):
                #         lines.append(line.format(c_type=c_data_type(v.dtype), varname=k, objname=v.obj.name,
                #                                  attrname=v.attribute))
                if isinstance(v, ArrayVariable):
                    try:
                        if isinstance(v, DynamicArrayVariable):
                            if v.dimensions == 1:
                                dyn_array_name = self.dynamic_arrays[v]
                                array_name = self.arrays[v]
                                line = '{c_type}* const {array_name} = &{dyn_array_name}[0];'
                                line = line.format(c_type=c_data_type(v.dtype),
                                                   array_name=array_name,
                                                   dyn_array_name=dyn_array_name)
                                lines.append(line)
                                line = 'const int _num{k} = {dyn_array_name}.size();'
                                line = line.format(k=k,
                                                   dyn_array_name=dyn_array_name)
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
            if not codeobj.template_name in ['stateupdate', 'threshold',
                                             'reset', 'synapses']:
                if isinstance(codeobj.code, MultiTemplate):
                    code = freeze(codeobj.code.cpp_file, ns)
                    code = code.replace('%CONSTANTS%', '\n'.join(
                        code_object_defs[codeobj.name]))
                    code = '#include "objects.h"\n' + code

                    writer.write('code_objects/' + codeobj.name + '.cpp', code)
                    self.source_files.append(
                        'code_objects/' + codeobj.name + '.cpp')
                    writer.write('code_objects/' + codeobj.name + '.h',
                                 codeobj.code.h_file)
                    self.header_files.append(
                        'code_objects/' + codeobj.name + '.h')

    def run(self, directory, use_GPU, with_output):
        if not with_output:
            stdout = open(os.devnull, 'w')
            stderr = open(os.devnull, 'w')
        else:
            stdout = None
            stderr = None
        start_time = time.time()
        gpu_arg = "1" if use_GPU else "0"
        if gpu_arg == "1":
            where = 'on GPU'
        else:
            where = 'on CPU'
        print 'executing genn binary %s ...' % where
        if os.sys.platform == 'win32':
            cmd = directory + "\\main.exe test " + str(
                self.run_duration) + " " + gpu_arg
            # os.system(cmd)
            call(cmd, cwd=directory, stdout=stdout, stderr=stderr)
        else:
            # print ["./main", "test", str(self.run_duration), gpu_arg]
            call(["./main", "test", str(self.run_duration), gpu_arg],
                 cwd=directory, stdout=stdout, stderr=stderr)
        self.has_been_run = True
        last_run_info = open(
            os.path.join(directory, 'results/last_run_info.txt'), 'r').read()
        self._last_run_time, self._last_run_completed_fraction = map(float,
                                                                     last_run_info.split())

        # The following is a verbatim copy of the respective code in
        # CPPStandaloneDevice.run. In the long run, we can hopefully implement
        # this on the device-independent level, see #761 and discussion in
        # #750.

        # Make sure that integration did not create NaN or very large values
        owners = [var.owner for var in self.arrays]
        # We don't want to check the same owner twice but var.owner is a
        # weakproxy which we can't put into a set. We therefore store the name
        # of all objects we already checked. Furthermore, under some specific
        # instances a variable might have been created whose owner no longer
        # exists (e.g. a `_sub_idx` variable for a subgroup) -- we ignore the
        # resulting reference error.
        already_checked = set()
        for owner in owners:
            try:
                if owner.name in already_checked:
                    continue
                if isinstance(owner, Group):
                    owner._check_for_invalid_states()
                    already_checked.add(owner.name)
            except ReferenceError:
                pass

    def compile_source(self, debug, directory, use_GPU):
        with std_silent(debug):
            if os.sys.platform == 'win32':
                if os.getenv('PROCESSOR_ARCHITECTURE') == "AMD64":
                    bitversion = 'x86_amd64'
                elif os.getenv('PROCESSOR_ARCHITEW6432') == "AMD64":
                    bitversion = 'x86_amd64'
                else:
                    bitversion = 'x86'

                # Users are required to set their path to "Visual Studio/VC", e.g.
                # setx VS_PATH "C:\Program Files (x86)\Microsoft Visual Studio 10.0"
                cmd = "\"" + os.getenv(
                    'VS_PATH') + "\\VC\\vcvarsall.bat\" " + bitversion
                cmd = cmd + " && genn-buildmodel.bat " + self.model_name + ".cpp"
                if not use_GPU:
                    cmd += ' -c'
                cmd += "&& nmake /f WINmakefile clean && nmake /f WINmakefile"
                call(cmd, cwd=directory)
            else:
                if not use_GPU:
                    call(["genn-buildmodel.sh", self.model_name + '.cpp', "-c"],
                         cwd=directory)
                    call(["make", "clean"], cwd=directory)
                    call(["make"], cwd=directory)
                else:
                    call(["genn-buildmodel.sh", self.model_name + '.cpp'],
                         cwd=directory)
                    call(["make", "clean"], cwd=directory)
                    call(["make"], cwd=directory)

    def add_parameter(self, model, varname, variable):
        model.parameters.append(varname)
        model.pvalue.append(repr(variable.value))

    def add_array_variable(self, model, varname, variable):
        model.variables.append(varname)
        model.variabletypes.append(c_data_type(variable.dtype))
        model.variablescope[varname] = 'brian'

    def add_array_variables(self, model, owner):
        for varname, variable in owner.variables.iteritems():
            if varname in ['_spikespace', 't', 'dt']:
                pass
            elif getattr(variable.owner, 'name', None) != owner.name:
                pass
            elif isinstance(variable, ArrayVariable):
                self.add_array_variable(model, varname, variable)

    def process_poisson_groups(self, objects, poisson_groups):
        for obj in poisson_groups:
            # throw error if events other than spikes are used
            if len(obj.events.keys()) > 1 or (len(
                    obj.events.keys()) == 1 and not obj.events.iterkeys().next() == 'spike'):
                raise NotImplementedError(
                    'Brian2GeNN does not support events that are not spikes')

            # Extract the variables
            neuron_model = neuronModel()
            neuron_model.name = obj.name
            neuron_model.N = obj.N
            self.add_array_variables(neuron_model, obj)
            support_lines = []
            suffix = '_thresholder';
            lines = neuron_model.thresh_cond_lines;
            codeobj = objects[obj.name + suffix].codeobj
            for k, v in codeobj.variables.iteritems():
                if k != 'dt' and isinstance(v, Constant):
                    if k not in neuron_model.parameters:
                        self.add_parameter(neuron_model, k, v)
                code = codeobj.code.cpp_file

            code = self.fix_random_generators(neuron_model, code)
            code = decorate(code, neuron_model.variables,
                            neuron_model.parameters).strip()
            lines.append(code)
            code = stringify(codeobj.code.h_file)
            support_lines.append(code)
            neuron_model.support_code_lines = support_lines
            self.neuron_models.append(neuron_model)
            self.groupDict[neuron_model.name] = neuron_model

    def process_neuron_groups(self, neuron_groups, objects):
        for obj in neuron_groups:
            # throw error if events other than spikes are used
            if len(obj.events.keys()) > 1 or (len(
                    obj.events.keys()) == 1 and not obj.events.iterkeys().next() == 'spike'):
                raise NotImplementedError(
                    'Brian2GeNN does not support events that are not spikes')
            # Extract the variables
            neuron_model = neuronModel()
            neuron_model.name = obj.name
            neuron_model.N = obj.N
            self.add_array_variables(neuron_model, obj)
            support_lines = []
            for suffix, lines in [('_stateupdater', neuron_model.code_lines),
                                  ('_run_regularly', neuron_model.code_lines),
                                  ('_thresholder',
                                   neuron_model.thresh_cond_lines),
                                  ('_resetter', neuron_model.reset_code_lines),
                                  ]:
                if obj.name + suffix not in objects:
                    if suffix == '_thresholder':
                        lines.append('0')
                    if suffix == '_resetter' and not (obj._refractory is False):
                        code = 'lastspike = t; \n not_refractory= 0;'
                        neuron_model, code = self.fix_random_generators(
                            neuron_model, code)
                        code = decorate(code, neuron_model.variables,
                                        neuron_model.parameters).strip()
                        lines.append(code)
                    continue

                codeobj = objects[obj.name + suffix].codeobj
                if codeobj is None:
                    continue

                for k, v in codeobj.variables.iteritems():
                    if k != 'dt' and isinstance(v, Constant):
                        if k not in neuron_model.parameters:
                            self.add_parameter(neuron_model, k, v)
                code = codeobj.code.cpp_file

                if (suffix == '_resetter') and not (obj._refractory is False):
                    code = code + '\n lastspike = t; \n not_refractory= 0;'
                code = self.fix_random_generators(neuron_model, code)
                code = decorate(code, neuron_model.variables,
                                neuron_model.parameters).strip()
                lines.append(code)
                code = stringify(codeobj.code.h_file)
                support_lines.append(code)
            neuron_model.support_code_lines = support_lines
            self.neuron_models.append(neuron_model)
            self.groupDict[neuron_model.name] = neuron_model

    def process_spikegenerators(self, spikegenerator_groups):
        for obj in spikegenerator_groups:
            spikegenerator_model = spikegeneratorModel()
            spikegenerator_model.name = obj.name
            spikegenerator_model.N = obj.N
            self.spikegenerator_models.append(spikegenerator_model)

    def process_synapses(self, synapse_groups):
        for obj in synapse_groups:
            synapse_model = synapseModel()
            synapse_model.name = obj.name
            if isinstance(obj.source, Subgroup):
                synapse_model.srcname = obj.source.source.name
                synapse_model.srcN = obj.source.source.variables[
                    'N'].get_value()
            else:
                synapse_model.srcname = obj.source.name
                synapse_model.srcN = obj.source.variables['N'].get_value()
            if isinstance(obj.target, Subgroup):
                synapse_model.trgname = obj.target.source.name
                synapse_model.trgN = obj.target.source.variables[
                    'N'].get_value()
            else:
                synapse_model.trgname = obj.target.name
                synapse_model.trgN = obj.target.variables['N'].get_value()
            synapse_model.connectivity = prefs.devices.genn.connectivity
            self.connectivityDict[obj.name] = synapse_model.connectivity

            for pathway in ['pre', 'post']:
                if hasattr(obj, pathway):
                    codeobj = getattr(obj, pathway).codeobj
                    # A little hack to support "write-protection" for refractory
                    # variables -- brian2genn currently requires that
                    # post-synaptic variables end with "_post"
                    if pathway == 'pre' and 'not_refractory' in codeobj.variables:
                        codeobj.variables['not_refractory_post'] = codeobj.variables['not_refractory']
                        codeobj.variable_indices['not_refractory_post'] = codeobj.variable_indices['not_refractory']
                        del codeobj.variables['not_refractory']
                        del codeobj.variable_indices['not_refractory']
                    self.collect_synapses_variables(synapse_model, pathway, codeobj)
                    if pathway == 'pre':
                        # Use the stored scalar delay (if any) for these synapses
                        synapse_model.delay = int(
                            self.delays.get(obj.name, 0.0) / defaultclock.dt_ + 0.5)
                    code = codeobj.code.cpp_file
                    code_lines = [line.strip() for line in code.split('\n')]
                    new_code_lines = []
                    if pathway == 'pre':
                        for line in code_lines:
                            if line.startswith('addtoinSyn'):
                                if synapse_model.connectivity == 'SPARSE':
                                    line = line.replace('_hidden_weightmatrix*', '')
                                    line = line.replace('_hidden_weightmatrix *', '')
                            new_code_lines.append(line)
                            if line.startswith('addtoinSyn'):
                                new_code_lines.append('$(updatelinsyn);')
                        code = '\n'.join(new_code_lines)

                    self.fix_synapses_code(synapse_model, pathway, codeobj,
                                           code)

            if obj.state_updater != None:
                codeobj = obj.state_updater.codeobj
                code = codeobj.code.cpp_file
                self.collect_synapses_variables(synapse_model, 'dynamics', codeobj)
                self.fix_synapses_code(synapse_model, 'dynamics', codeobj,
                                       code)

            if (hasattr(obj, '_genn_post_write_var')):
                synapse_model.postSyntoCurrent = '0; $(' + obj._genn_post_write_var.replace(
                    '_post', '') + ') += $(inSyn); $(inSyn)= 0'
            else:
                synapse_model.postSyntoCurrent = '0'
            self.synapse_models.append(synapse_model)
            self.groupDict[synapse_model.name] = synapse_model

    def collect_synapses_variables(self, synapse_model, pathway, codeobj):
        identifiers = set()
        for code in codeobj.code.values():
            identifiers |= get_identifiers(code)
        indices = codeobj.variable_indices
        for k, v in codeobj.variables.iteritems():
            if k in ['_spikespace', 't', 'dt'] or k not in identifiers:
                pass
            elif isinstance(v, Constant):
                if k not in synapse_model.parameters:
                    self.add_parameter(synapse_model, k, v)
            elif isinstance(v, ArrayVariable):
                if indices[k] == '_idx':
                    if k not in synapse_model.variables:
                        self.add_array_variable(synapse_model, k, v)
                else:
                    index = indices[k]
                    if (pathway in ['pre', 'post'] and
                                index == '_{}synaptic_idx'.format(pathway)):
                        raise NotImplementedError('brian2genn does not support '
                                                'references to {pathway}-'
                                                'synaptic variables in '
                                                'on_{pathway} '
                                                'statements.'.format(pathway=pathway))
                    if k not in synapse_model.external_variables:
                        synapse_model.external_variables.append(k)
            elif isinstance(v, Subexpression):
                raise NotImplementedError(
                    'Brian2genn does not support the use of '
                    'subexpressions in synaptic statements')

    def fix_synapses_code(self, synapse_model, pathway, codeobj, code):
        if synapse_model.connectivity == 'DENSE':
            code = 'if (_hidden_weightmatrix != 0.0) {' + code + '}'
        code = self.fix_random_generators(synapse_model, code)
        thecode = decorate(code, synapse_model.variables,
                           synapse_model.parameters, False).strip()
        thecode = decorate(thecode, synapse_model.external_variables,
                           [], True).strip()
        synapse_model.main_code_lines[pathway] = thecode
        code = stringify(codeobj.code.h_file)
        synapse_model.support_code_lines[pathway] = code

    def process_spike_monitors(self, spike_monitors):
        for obj in spike_monitors:
            if obj.event != 'spike':
                raise NotImplementedError(
                    'GeNN does not yet support event monitors for non-spike events.');
            sm = spikeMonitorModel()
            sm.name = obj.name
            if (hasattr(obj, 'when')):
                if (not obj.when in ['end', 'thresholds']):
                    # GeNN always records in the end slot but this should almost never make a difference and
                    # we therefore do not raise a warning if the SpikeMonitor records in the default thresholds
                    # slot. We do raise a NotImplementedError if the user manually changed the time slot to
                    # something else -- there was probably a reason for doing it.
                    raise NotImplementedError(
                        "Spike monitor {!s} has 'when' property '{!s}' which is not supported in GeNN, defaulting to 'end'.".format(
                            sm.name, obj.when))
            src = obj.source
            if isinstance(src, Subgroup):
                src = src.source
            sm.neuronGroup = src.name
            if (isinstance(src, SpikeGeneratorGroup)):
                sm.notSpikeGeneratorGroup = False;
            self.spike_monitor_models.append(sm)
            self.header_files.append(
                'code_objects/' + sm.name + '_codeobject.h')

        # ------------------------------------------------------------------------------
        # Process rate monitors

    def process_rate_monitors(self, rate_monitors):
        for obj in rate_monitors:
            sm = rateMonitorModel()
            sm.name = obj.name
            if (hasattr(obj, 'when')):
                if (not obj.when == 'end'):
                    logger.warn(
                        "Rate monitor {!s} has 'when' property '{!s}' which is not supported in GeNN, defaulting to 'end'.".format(
                            sm.name, obj.when))
            src = obj.source
            if isinstance(src, Subgroup):
                src = src.source
                print src
            sm.neuronGroup = src.name
            if (isinstance(src, SpikeGeneratorGroup)):
                sm.notSpikeGeneratorGroup = False;
            self.rate_monitor_models.append(sm)
            self.header_files.append(
                'code_objects/' + sm.name + '_codeobject.h')

    def process_state_monitors(self, directory, state_monitors, writer):
        for obj in state_monitors:
            sm = stateMonitorModel()
            sm.name = obj.name
            src = obj.source
            if isinstance(src, Subgroup):
                src = src.source
            sm.monitored = src.name
            sm.when = obj.when
            if not (sm.when == 'start' or sm.when == 'end'):
                logger.warn(
                    "State monitor {!s} has 'when' property '{!s}' which is not supported in GeNN, defaulting to 'end'.".format(
                        sm.name, sm.when))
                sm.when = 'end'
            if isinstance(src, Synapses):
                sm.isSynaptic = True
                sm.srcN = src.source.variables['N'].get_value()
                sm.trgN = src.target.variables['N'].get_value()
                sm.connectivity = self.connectivityDict[src.name]
            else:
                sm.isSynaptic = False
                sm.N = src.variables['N'].get_value()
            for varname in obj.record_variables:
                if isinstance(src.variables[varname], Subexpression):
                    extract_source_variables(src.variables, varname,
                                             sm.variables)
                elif isinstance(src.variables[varname], Constant):
                    logger.warn(
                        "variable '%s' is a constant - not monitoring" % varname)
                elif varname not in self.groupDict[sm.monitored].variables:
                    logger.warn(
                        "variable '%s' is unused - not monitoring" % varname)
                else:
                    sm.variables.append(varname)

            self.state_monitor_models.append(sm)
            self.header_files.append(
                'code_objects/' + sm.name + '_codeobject.h')

    def generate_model_source(self, writer):
        synapses_classes_tmp = CPPStandaloneCodeObject.templater.synapses_classes(
            None, None)
        writer.write('synapses_classes.*', synapses_classes_tmp)
        model_tmp = GeNNCodeObject.templater.model(None, None,
                                                   neuron_models=self.neuron_models,
                                                   spikegenerator_models=self.spikegenerator_models,
                                                   synapse_models=self.synapse_models,
                                                   dtDef=self.dtDef,
                                                   model_name=self.model_name,
                                                   )
        writer.write(self.model_name + '.cpp', model_tmp)

    def generate_main_source(self, writer, main_lines):
        runner_tmp = GeNNCodeObject.templater.main(None, None,
                                                   neuron_models=self.neuron_models,
                                                   synapse_models=self.synapse_models,
                                                   model_name=self.model_name,
                                                   main_lines=main_lines,
                                                   header_files=self.header_files,
                                                   source_files=self.source_files,
                                                   )
        writer.write('main.*', runner_tmp)

    def generate_engine_source(self, writer):
        maximum_run_time = self._maximum_run_time
        if maximum_run_time is not None:
            maximum_run_time = float(maximum_run_time)
        engine_tmp = GeNNCodeObject.templater.engine(None, None,
                                                     neuron_models=self.neuron_models,
                                                     spikegenerator_models=self.spikegenerator_models,
                                                     synapse_models=self.synapse_models,
                                                     spike_monitor_models=self.spike_monitor_models,
                                                     rate_monitor_models=self.rate_monitor_models,
                                                     state_monitor_models=self.state_monitor_models,
                                                     model_name=self.model_name,
                                                     maximum_run_time=maximum_run_time
                                                     )
        writer.write('engine.*', engine_tmp)

    def generate_makefile(self, directory, use_GPU):
        if os.sys.platform == 'win32':
            Makefile_tmp = GeNNCodeObject.templater.WINmakefile(None, None,
                                                                neuron_models=self.neuron_models,
                                                                model_name=self.model_name,
                                                                ROOTDIR=os.path.abspath(
                                                                    directory),
                                                                source_files=self.source_files,
                                                                prefs=prefs,
                                                                use_GPU=use_GPU
                                                                )
            open(os.path.join(directory, 'WINmakefile'), 'w').write(
                Makefile_tmp)
        else:
            Makefile_tmp = GeNNCodeObject.templater.GNUmakefile(None, None,
                                                                neuron_models=self.neuron_models,
                                                                model_name=self.model_name,
                                                                ROOTDIR=os.path.abspath(
                                                                    directory),
                                                                source_files=self.source_files,
                                                                prefs=prefs,
                                                                use_GPU=use_GPU
                                                                )
            open(os.path.join(directory, 'GNUmakefile'), 'w').write(
                Makefile_tmp)

        # ------------------------------------------------------------------------------
        # Compile it

    def generate_objects_source(self, arange_arrays, net, static_array_specs,
                                synapses, writer):
        # ------------------------------------------------------------------------------
        # create the objects.cpp and objects.h code
        the_objects = self.code_objects.values()
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
            networks=[net],
            get_array_filename=self.get_array_filename,
            get_array_name=self.get_array_name,
            code_objects=the_objects
        )
        writer.write('objects.*', arr_tmp)
        self.header_files.append('objects.h')
        self.source_files.append('objects.cpp')

    def copy_source_files(self, writer, directory):
        # Copies brianlib, spikequeue and randomkit
        super(GeNNDevice, self).copy_source_files(writer, directory)

        # Copy the b2glib directory
        b2glib_dir = os.path.join(
            os.path.split(inspect.getsourcefile(GeNNCodeObject))[0],
            'b2glib')
        b2glib_files = copy_directory(b2glib_dir,
                                      os.path.join(directory, 'b2glib'))
        for file in b2glib_files:
            if file.lower().endswith('.cpp'):
                self.source_files.append('b2glib/' + file)
            elif file.lower().endswith('.h'):
                self.header_files.append('b2glib/' + file)

    def network_run(self, net, duration, report=None, report_period=10*second,
                    namespace=None, profile=False, level=0, **kwds):
        # We quietly ignore the profile argument instead of raising a warning
        # every time...

        if kwds:
            logger.warn(('Unsupported keyword argument(s) provided for run: '
+ '%s') % ', '.join(kwds.keys()))
            
        if self.run_duration is not None:
            raise NotImplementedError('Only a single run statement is supported for the genn device.')
        self.run_duration = float(duration)
        for obj in net.objects:
            if obj.clock.name is not 'defaultclock':
                raise NotImplementedError('Multiple clocks are not supported for the genn device')

        for obj in net.objects:
            if hasattr(obj,'_linked_variables'):
                    if len(obj._linked_variables) > 0:
                        raise NotImplementedError('The genn device does not support linked variables')
        for obj in net.objects:
            if hasattr(obj, 'template'):
                if obj.template in [ 'summed_variable' ]:
                    raise NotImplementedError('The function of %s is not yet supported in GeNN.' % obj.template)
                                
        print 'running brian code generation ...'
        super(GeNNDevice, self).network_run(net=net, duration=duration, report=report, report_period=report_period, namespace=namespace, level=level+1)

#------------------------------------------------------------------------------
# End of GeNNDevice
#------------------------------------------------------------------------------

genn_device = GeNNDevice()

all_devices['genn'] = genn_device
