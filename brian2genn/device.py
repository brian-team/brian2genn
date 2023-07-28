'''
Module implementing the bulk of the brian2genn interface by defining the "genn" device.
'''

import os
import platform
import re
import shutil
import sys

from pkg_resources import parse_version
from subprocess import call, check_call, CalledProcessError
import inspect
from collections import defaultdict
import tempfile
import itertools
import numpy
import numbers
from collections import Counter

from brian2.codegen.cpp_prefs import get_msvc_env
from brian2.codegen.translation import make_statements
from brian2.input.poissoninput import PoissonInput
from brian2.spatialneuron.spatialneuron import (SpatialNeuron,
                                                SpatialStateUpdater)
from brian2.units import second
from brian2.codegen.generators.cpp_generator import (c_data_type,
                                                     CPPCodeGenerator)
from brian2.codegen.templates import MultiTemplate
from brian2.core.clocks import defaultclock
from brian2.core.variables import *
from brian2.core.functions import Function
from brian2.core.network import _get_all_objects
from brian2.devices.device import all_devices
from brian2.devices.cpp_standalone.device import CPPStandaloneDevice
from brian2.parsing.rendering import CPPNodeRenderer
from brian2.synapses.synapses import Synapses, SynapticPathway
from brian2.monitors.spikemonitor import SpikeMonitor
from brian2.monitors.ratemonitor import PopulationRateMonitor
from brian2.monitors.statemonitor import StateMonitor
from brian2.utils.filetools import copy_directory, ensure_directory
from brian2.utils.stringtools import word_substitute, get_identifiers
from brian2.groups.group import Group, CodeRunner
from brian2.groups.neurongroup import (NeuronGroup, StateUpdater, Resetter,
                                       Thresholder, SubexpressionUpdater)
from brian2.groups.subgroup import Subgroup
from brian2.input.poissongroup import PoissonGroup
from brian2.input.spikegeneratorgroup import *
from brian2.synapses.synapses import StateUpdater as SynapsesStateUpdater
from brian2.utils.logger import get_logger, std_silent
from brian2.devices.cpp_standalone.codeobject import CPPStandaloneCodeObject
from brian2.devices.cpp_standalone.device import CPPWriter
from brian2 import prefs
from .codeobject import GeNNCodeObject, GeNNUserCodeObject
from .genn_generator import get_var_ndim, GeNNCodeGenerator

__all__ = ['GeNNDevice']

logger = get_logger('brian2.devices.genn')


def stringify(code):
    '''
    Helper function to prepare multiline strings (potentially including
    quotation marks) to be included in strings.

    Parameters
    ----------
    code : str
        The code to convert.
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
        if isinstance(v, str):
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


def get_gcc_compile_args():
    '''
    Get the compile args for GCC based on the users preferences. Uses Brian's
    preferences for the C++ compilation (either `codegen.cpp.extra_compile_args`
    or `codegen.cpp.extra_compile_args_gcc`).

    Returns
    -------
    (compile_args_gcc, compile_args_msvc, compile_args_nvcc) : (str, str, str)
        Tuple with the respective compiler arguments (as strings).
    '''
    if prefs.codegen.cpp.extra_compile_args is not None:
        args = ' '.join(prefs.codegen.cpp.extra_compile_args)
        compile_args_gcc = args
    else:
        compile_args_gcc = ' '.join(prefs.codegen.cpp.extra_compile_args_gcc)

    return compile_args_gcc


def decorate(code, variables, shared_variables, parameters, do_final=True):
    '''
    Support function for inserting GeNN-specific "decorations" for variables and
    parameters, such as $(.).
    '''
    # this is a bit of a hack, it should be part of the language probably
    for v in itertools.chain(variables, shared_variables, parameters):
        code = word_substitute(code, {v: '$(' + v + ')'})
    code = word_substitute(code, {'dt': 'DT'}).strip()
    if do_final:
        code = stringify(code)
        code = re.sub(r'addtoinSyn\s*=\s*(.*);', r'$(addToInSyn,\1);', code)
        code = word_substitute(code, {'_hidden_weightmatrix': '$(_hidden_weightmatrix)'})
    return code


def extract_source_variables(variables, varname, smvariables):
    '''Support function to extract the "atomic" variables used in a variable
    that is of instance `Subexpression`.
    '''
    identifiers = get_identifiers(variables[varname].expr)
    for vnm, var in variables.items():
        if vnm in identifiers:
            if var in defaultclock.variables.values():
                raise NotImplementedError('Recording an expression that depends on '
                                          'the time t or the timestep dt is '
                                          'currently not supported in Brian2GeNN')
            elif isinstance(var, ArrayVariable):
                smvariables.append(vnm)
            elif isinstance(var, Subexpression):
                smvariables = extract_source_variables(variables, vnm,
                                                       smvariables)
    return smvariables

def find_executable(executable):
    """Tries to find 'executable' in the path

    Modified version of distutils.spawn.find_executable as
    this has stupid rules for extensions on Windows.
    Returns the complete filename or None if not found.
    """
    path = os.environ.get('PATH', os.defpath)

    paths = path.split(os.pathsep)

    for p in paths:
        f = os.path.join(p, executable)
        if os.path.isfile(f):
            # the file exists, we have a shot at spawn working
            return f
    return None

class DelayedCodeObject:
    '''
    Dummy class used for delaying the CodeObject creation of stateupdater,
    thresholder, and resetter of a NeuronGroup (which will all be merged into a
    single code object).
    '''
    def __init__(self, owner, name, abstract_code, variables, variable_indices,
                 override_conditional_write):
        self.owner = owner
        self.name = name
        self.abstract_code = abstract_code
        self.variables = variables
        self.variable_indices = variable_indices
        self.override_conditional_write = override_conditional_write

    def before_run(self):
        pass

    def after_run(self):
        pass


class neuronModel:
    '''
    Class that contains all relevant information of a neuron model.
    '''

    def __init__(self):
        self.name = ''
        self.clock = None
        self.N = 0
        self.variables = []
        self.variabletypes = []
        self.variablescope = dict()
        self.shared_variables = []
        self.shared_variabletypes = []
        self.parameters = []
        self.pvalue = []
        self.code_lines = []
        self.thresh_cond_lines = []
        self.reset_code_lines = []
        self.support_code_lines = []


class spikegeneratorModel:
    '''
    Class that contains all relevant information of a spike generator group.
    '''
    def __init__(self):
        self.name = ''
        self.codeobject_name = ''
        self.N = 0


class synapseModel:
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
        self.shared_variables = []
        self.shared_variabletypes = []
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
        self.summed_variables= None

class spikeMonitorModel:
    '''
    Class the contains all relevant information about a spike monitor.
    '''
    def __init__(self):
        self.name = ''
        self.codeobject_name = ''
        self.neuronGroup = ''
        self.notSpikeGeneratorGroup = True


class rateMonitorModel:
    '''
    CLass that contains all relevant information about a rate monitor.
    '''
    def __init__(self):
        self.name = ''
        self.codeobject_name = ''
        self.neuronGroup = ''
        self.notSpikeGeneratorGroup = True


class stateMonitorModel:
    '''
    Class that contains all relvant information about a state monitor.
    '''
    def __init__(self):
        self.name = ''
        self.codeobject_name = ''
        self.order = 0
        self.monitored = ''
        self.src = None
        self.isSynaptic = False
        self.variables = []
        self.srcN = 0
        self.trgN = 0
        self.when = ''
        self.step = 1
        self.connectivity = ''


# ------------------------------------------------------------------------------
# Start of GeNNDevice
# ------------------------------------------------------------------------------

class GeNNDevice(CPPStandaloneDevice):
    '''
    The main "genn" device. This does most of the translation work from Brian 2
    generated code to functional GeNN code, assisted by the "GeNN language".
    '''
    def __init__(self):
        super().__init__()
        # Remember whether we have already passed the "run" statement
        self.run_statement_used = False
        self.network_schedule = ['start', 'synapses', 'groups', 'thresholds',
                                 'resets', 'end']
        self.neuron_models = []
        self.spikegenerator_models = []
        self.synapse_models = []
        self.max_row_length_include= []
        self.max_row_length_run_calls= []
        self.max_row_length_synapses= set()
        self.max_row_length_code_objects= {}
        self.delays = {}
        self.spike_monitor_models = []
        self.rate_monitor_models = []
        self.state_monitor_models = []
        self.run_regularly_read_write = {}
        self.run_duration = None
        self.net = None
        self.net_objects = set()
        self.simple_code_objects = {}
        self.report_func = ''
        self.src_counts= dict()
        self.trg_counts= dict()
        #: Set of all source and header files (to be included in runner)
        self.source_files = set()
        self.header_files = set()

        self.connectivityDict = dict()
        self.groupDict = dict()

        # Overwrite the code slots defined in standard C++ standalone
        self.code_lines = {'before_start': [],
                           'after_start': [],
                           'before_network_run': [],
                           'after_network_run': [],
                           'before_end': [],
                           'after_end': []}

        #: Use GeNN's kernel timings?
        self.kernel_timings = False

    def insert_code(self, slot, code):
        '''
        Insert custom C++ code directly into ``main.cpp``. The available slots
        are:

        ``before_start`` / ``after_start``
            Before/after allocating memory for the arrays and loading arrays from
            disk.
        ``before_network_run`` / ``after_network_run``
            Before/after calling GeNN's ``run`` function.
        ``before_end`` / ``after_end``
            Before/after writing results to disk and deallocating memory.

        Parameters
        ----------
        slot : str
            The name of the slot where the code will be placed (see above for
            list of available slots).
        code : str
            The C++ code that should be inserted.
        '''
        # Only overwritten so that we can have custom documentation
        super().insert_code(slot, code)

    def activate(self, build_on_run=True, **kwargs):
        new_prefs = {'codegen.generators.cpp.restrict_keyword': '__restrict',
                     'codegen.loop_invariant_optimisations': False,
                     'core.network.default_schedule': ['start', 'synapses',
                                                       'groups', 'thresholds',
                                                       'resets', 'end']}
        changed = []
        for new_pref, new_value in new_prefs.items():
            if prefs[new_pref] != new_value:
                changed.append(new_pref)
                prefs[new_pref] = new_value

        if changed:
            logger.info('The following preferences have been changed for '
                        'Brian2GeNN, reset them manually if you use a '
                        'different device later in the same script: '
                        '{}'.format(', '.join(changed)), once=True)
            prefs._backup()
        super().activate(build_on_run, **kwargs)

    def code_object_class(self, codeobj_class=None, *args, **kwds):
        if codeobj_class is None:
            codeobj_class = GeNNUserCodeObject
        return codeobj_class

    def code_object(self, owner, name, abstract_code, variables, template_name,
                    variable_indices, codeobj_class=None, template_kwds=None,
                    override_conditional_write=None, **kwds):
        '''
        Processes abstract code into code objects and stores them in different
        arrays for `GeNNCodeObjects` and `GeNNUserCodeObjects`.
        '''
        if '_run_regularly_' in name:
            variables['N'] = owner.variables['N']
            # Add an extra code object that executes the scalar code of
            # the run_regularly operation (will be directly called from
            # engine.cpp)
            codeobj = super().code_object(owner, name,
                                          abstract_code,
                                          variables,
                                          'stateupdate',
                                          variable_indices,
                                          codeobj_class=CPPStandaloneCodeObject,
                                          template_kwds=template_kwds,
                                          override_conditional_write=override_conditional_write,
                                          )

            # FIXME: The following is redundant with what is done during
            # the code object creation above. At the moment, the code
            # object does not allow us to access the information we
            # need (variables that are read/written by the run_regularly
            # code), though.
            generator = CPPCodeGenerator(variables,
                                         variable_indices, owner=owner,
                                         iterate_all=False,
                                         codeobj_class=GeNNUserCodeObject,
                                         name=name,
                                         template_name='run_regularly_scalar_code',
                                         override_conditional_write=override_conditional_write,
                                         allows_scalar_write=True)
            scalar_statements, vector_statements = make_statements(abstract_code[None],
                                                                   variables,
                                                                   numpy.float64)
            read_sc, write_sc, _ = generator.array_read_write(scalar_statements)
            read_ve, write_ve, _ = generator.array_read_write(vector_statements)

            # We do not need to copy over constant values from the GPU
            read = {r for r in (read_sc | read_ve) if not variables[r].constant}
            self.run_regularly_read_write[codeobj.name] = {'read': read,
                                                           'write': write_sc | write_ve}

        elif ((template_name in ['stateupdate', 'threshold', 'reset'] and
               isinstance(owner, NeuronGroup)) or (template_name in ['summed_variable']
                                                   and isinstance(owner, Synapses))):
            # Delay the code generation process, we want to merge them into one
            # code object later
            codeobj = DelayedCodeObject(owner=owner,
                                        name=name,
                                        abstract_code=abstract_code,
                                        variables=variables,
                                        variable_indices=variable_indices,
                                        override_conditional_write=override_conditional_write)
            # We need to clear the array cache for these at some point (normally
            # would be done in cpp_standalone.device.code_object()
            # I will do it here but not sure this is the best place
            # I am also not sure whether "written_readonly_vars" apply here
            # I WILL ASSUME NOT
            for var in codeobj.variables.values():
                if (isinstance(var, ArrayVariable) and
                    not var.read_only):
                    self.array_cache[var] = None
            self.simple_code_objects[name] = codeobj

        elif template_name in ['reset', 'synapses', 'stateupdate', 'threshold']:
            codeobj_class = GeNNCodeObject
            codeobj = super().code_object(owner, name,
                                          abstract_code,
                                          variables,
                                          template_name,
                                          variable_indices,
                                          codeobj_class=codeobj_class,
                                          template_kwds=template_kwds,
                                          override_conditional_write=override_conditional_write,
                                                          )
            self.simple_code_objects[codeobj.name] = codeobj
        else:
            codeobj_class = GeNNUserCodeObject
            if ('_synapses_create_generator_' in name) or ('_synapses_create_array_' in name):
                # Here we process max_row_length for synapses
                # the strategy is to do a dry run of connection generationin in the model definition
                # function that has the same random numbers and just counts synaptic connections
                # rather than generating them for real
                generator= '_synapses_create_generator_' in name
                mrl_name= '%s_max_row_length' % owner.name
                i= 1
                while mrl_name in self.max_row_length_code_objects:
                    mrl_name= '%s_max_row_length_%d' % (owner.name, i)
                    i= i+1
                if generator:
                    mrl_template_name= 'max_row_length_generator'
                else:
                    mrl_template_name='max_row_length_array'
                codeobj = super().code_object(owner, mrl_name,
                                              abstract_code,
                                              variables,
                                              mrl_template_name,
                                              variable_indices,
                                              codeobj_class=codeobj_class,
                                              template_kwds=template_kwds,
                                              override_conditional_write=override_conditional_write,
                )
                #self.code_objects['%s_max_row_length' % owner.name] = codeobj
                self.code_objects.pop(mrl_name, None)   # remove this from the normal list of code objects
                self.max_row_length_code_objects[mrl_name]= codeobj # add to this dict instead
                self.max_row_length_synapses.add(owner.name)
                self.max_row_length_include.append('#include "code_objects/%s.cpp"' % codeobj.name)
                self.max_row_length_run_calls.append('_run_%s();' % mrl_name)

            codeobj = super().code_object(owner, name,
                                          abstract_code,
                                          variables,
                                          template_name,
                                          variable_indices,
                                          codeobj_class=codeobj_class,
                                          template_kwds=template_kwds,
                                          override_conditional_write=override_conditional_write,
                                          )
            # FIXME: is this actually necessary or is it already added by the super?
            self.code_objects[codeobj.name] = codeobj
        return codeobj

    # The following two methods are only overwritten to catch assignments to the
    # delay variable -- GeNN does not support heterogeneous delays
    def fill_with_array(self, var, arr):
        if isinstance(var.owner, Synapses) and var.name == 'delay':
            # Assigning is only allowed if the variable has been declared in the
            # Synapse constructor and is therefore scalar
            if not var.scalar:
                raise NotImplementedError(
                    'GeNN does not support assigning to the '
                    'delay variable -- set the delay for all'
                    'synapses (heterogeneous delays are not '
                    'supported) as an argument to the '
                    'Synapses initializer.')
            else:
                # We store the delay so that we can later access it
                self.delays[var.owner.name] = numpy.asarray(arr).item()
        elif isinstance(var.owner, NeuronGroup) and var.name == 'lastspike':
            # Workaround for versions of Brian 2 <= 2.1.3.1 which initialize
            # a NeuronGroup's lastspike variable to -inf, no longer supported
            # by the new implementation of the timestep function
            if arr == -numpy.inf:
                logger.warn('Initializing the lastspike variable with -10000s '
                            'instead of -inf to copy the behaviour of Brian 2 '
                            'for versions >= 2.2 -- upgrade Brian 2 to remove '
                            'this warning',
                            name_suffix='lastspike_inf', once=True)
                arr = numpy.array(-1e4)
        super().fill_with_array(var, arr)

    def variableview_set_with_index_array(self, variableview, item,
                                          value, check_units):
        var = variableview.variable
        if isinstance(var.owner, Synapses) and var.name == 'delay':
            raise NotImplementedError('GeNN does not support assigning to the '
                                      'delay variable -- set the delay for all '
                                      'synapses (heterogeneous delays are not '
                                      'supported) as an argument to the '
                                      'Synapses initializer.')
        super().variableview_set_with_index_array(variableview,
                                                                  item,
                                                                  value,
                                                                  check_units)

    def variableview_set_with_expression(self, variableview, item, code, run_namespace, check_units=True):
        var = variableview.variable
        if isinstance(var.owner, Synapses) and var.name == 'delay':
            raise NotImplementedError('GeNN does not support assigning to the '
                                      'delay variable -- set the delay for all '
                                      'synapses (heterogeneous delays are not '
                                      'supported) as an argument to the '
                                      'Synapses initializer.')
        variableview.set_with_expression.original_function(variableview,
                                                           item,
                                                           code,
                                                           run_namespace,
                                                           check_units)

    def variableview_set_with_expression_conditional(self, variableview, cond,
                                                     code, run_namespace,
                                                     check_units=True):
        var = variableview.variable
        if isinstance(var.owner, Synapses) and var.name == 'delay':
            raise NotImplementedError('GeNN does not support assigning to the '
                                      'delay variable -- set the delay for all '
                                      'synapses (heterogeneous delays are not '
                                      'supported) as an argument to the '
                                      'Synapses initializer.')
        variableview.set_with_expression_conditional.original_function(variableview,
                                                                       cond,
                                                                       code,
                                                                       run_namespace,
                                                                       check_units)

    # --------------------------------------------------------------------------
    def make_main_lines(self):
        '''
        Generates the code lines that handle initialisation of Brian 2
        cpp_standalone type arrays. These are then translated into the
        appropriate GeNN data structures in separately generated code.
        '''
        main_lines = []
        procedures = [('', main_lines)]
        runfuncs = {}
        for func, args in self.main_queue:
            # explicitly exclude spike queue related code objects here:
            if (func.endswith('run_code_object') and
                    (args[0].name.endswith('_initialise_queue') or
                     args[0].name.endswith('_push_spikes'))):
                continue
            if func == 'run_code_object':
                codeobj, = args
                if self.run_statement_used:
                    raise NotImplementedError('Cannot execute code after the '
                                              'run statement '
                                              '(CodeObject: %s)' % codeobj.name)
                main_lines.append('_run_%s();' % codeobj.name)
            elif func == 'before_run_code_object':
                codeobj, = args
                main_lines.append('_before_run_%s();' % codeobj.name)
            elif func == 'after_run_code_object':
                codeobj, = args
                main_lines.append('_after_run_%s();' % codeobj.name)
            elif func == 'run_network':
                net, netcode = args
                # do nothing
            elif func == 'set_by_constant':
                arrayname, value, is_dynamic = args
                size_str = arrayname + '.size()' if is_dynamic else '_num_' + arrayname
                code = '''
                for(int i=0; i<{size_str}; i++)
                {{
                    {arrayname}[i] = {value};
                }}
                '''.format(arrayname=arrayname, size_str=size_str,
                           value=CPPNodeRenderer().render_expr(repr(value)))
                main_lines.extend(code.split('\n'))
            elif func == 'set_by_array':
                arrayname, staticarrayname, is_dynamic = args
                size_str = arrayname + '.size()' if is_dynamic else '_num_' + arrayname
                code = '''
                for(int i=0; i<{size_str}; i++)
                {{
                    {arrayname}[i] = {staticarrayname}[i];
                }}
                '''.format(arrayname=arrayname, size_str=size_str,
                           staticarrayname=staticarrayname)
                main_lines.extend(code.split('\n'))
            elif func == 'set_by_single_value':
                arrayname, item, value = args
                code = '{arrayname}[{item}] = {value};'.format(
                    arrayname=arrayname,
                    item=item,
                    value=value)
                main_lines.extend([code])
            elif func == 'set_array_by_array':
                arrayname, staticarrayname_index, staticarrayname_value = args
                code = '''
                for(int i=0; i<_num_{staticarrayname_index}; i++)
                {{
                    {arrayname}[{staticarrayname_index}[i]] = {staticarrayname_value}[i];
                }}
                '''.format(arrayname=arrayname,
                           staticarrayname_index=staticarrayname_index,
                           staticarrayname_value=staticarrayname_value)
                main_lines.extend(code.split('\n'))
            elif func == 'resize_array':
                array_name, new_size = args
                main_lines.append("{array_name}.resize({new_size});".format(
                    array_name=array_name,
                    new_size=new_size))
            elif func == 'insert_code':
                main_lines.append(args)
            elif func == 'start_run_func':
                name, include_in_parent = args
                if include_in_parent:
                    main_lines.append('%s();' % name)
                main_lines = []
                procedures.append((name, main_lines))
            elif func == 'end_run_func':
                name, include_in_parent = args
                name, main_lines = procedures.pop(-1)
                runfuncs[name] = main_lines
                name, main_lines = procedures[-1]
            elif func == 'seed':
                raise NotImplementedError('Setting a seed is currently '
                                          'not supported')
            else:
                raise TypeError("Unknown main queue function type " + func)

        # generate the finalisations
        for codeobj in self.code_objects.values():
            if hasattr(codeobj.code, 'main_finalise'):
                main_lines.append(codeobj.code.main_finalise)
        return main_lines

    def fix_random_generators(self, model, code):
        '''
        Translates cpp_standalone style random number generator calls into
        GeNN- compatible calls by replacing the cpp_standalone
        `_vectorisation_idx` argument with the GeNN `_seed` argument.
        '''
        # TODO: In principle, _vectorisation_idx is an argument to any
        # function that does not take any arguments -- in practice, random
        # number generators are the only argument-less functions that are
        # commonly used. We cannot check for explicit names `_rand`, etc.,
        # since multiple uses of binomial or PoissonInput will need to names
        # that we cannot easily predict (poissoninput_binomial_2, etc.)
        if '_vectorisation_idx)' in code:
            code = code.replace('_vectorisation_idx)',
                                '_seed)')
            if not '_seed' in model.variables:
                model.variables.append('_seed')
                model.variabletypes.append('uint64_t')
                model.variablescope['_seed'] = 'genn'

        return code

    # --------------------------------------------------------------------------
    def build(self, directory='GeNNworkspace', compile=True, run=True,
              use_GPU=True,
              debug=False, with_output=True, direct_call=True):
        '''
        This function does the main post-translation work for the genn device.
        It uses the code generated during/before run() and extracts information
        about neuron groups, synapse groups, monitors, etc. that is then
        formatted for use in GeNN-specific templates. The overarching strategy
        of the brian2genn interface is to use cpp_standalone code generation
        and templates for most of the "user-side code" (in the meaning defined
        in GeNN) and have GeNN-specific templates for the model definition and
        the main code for the executable that pulls everything together (in
        main.cpp and engine.cpp templates). The handling of input/output
        arrays for everything is lent from cpp_standalone and the
        cpp_standalone arrays are then translated into GeNN-suitable data
        structures using the static (not code-generated) b2glib library
        functions. This means that the GeNN specific cod only has to be
        concerned about executing the correct model and feeding back results
        into the appropriate cpp_standalone data structures.
        '''

        print('building genn executable ...')

        if directory is None:  # used during testing
            directory = tempfile.mkdtemp()

        # Start building the project
        self.project_dir = directory
        ensure_directory(directory)
        for d in ['code_objects', 'results', 'static_arrays']:
            ensure_directory(os.path.join(directory, d))

        writer = CPPWriter(directory)

        logger.debug(
            "Writing GeNN project to directory " + os.path.normpath(directory))

        arange_arrays = self.arange_arrays

        # write the static arrays
        for code_object in self.code_objects.values():
            for var in code_object.variables.values():
                if isinstance(var, Function):
                    self._insert_func_namespace(var, code_object,
                                                self.static_arrays)

        logger.debug("static arrays: " + str(sorted(self.static_arrays.keys())))
        static_array_specs = []
        for name, arr in sorted(self.static_arrays.items()):
            arr.tofile(os.path.join(directory, 'static_arrays', name))
            static_array_specs.append(
                (name, c_data_type(arr.dtype), arr.size, name))

        net_objects = self.net_objects

        main_lines = self.make_main_lines()

        # assemble the model descriptions:
        objects = {obj.name: obj for obj in net_objects}
        neuron_groups = [obj for obj in net_objects if
                         isinstance(obj, NeuronGroup)]
        poisson_groups = [obj for obj in net_objects if
                          isinstance(obj, PoissonGroup)]
        spikegenerator_groups = [obj for obj in net_objects if
                                 isinstance(obj, SpikeGeneratorGroup)]

        synapse_groups = [obj for obj in net_objects if
                          isinstance(obj, Synapses)]

        spike_monitors = [obj for obj in net_objects if
                          isinstance(obj, SpikeMonitor)]
        rate_monitors = [obj for obj in net_objects if
                         isinstance(obj, PopulationRateMonitor)]
        state_monitors = [obj for obj in net_objects if
                          isinstance(obj, StateMonitor)]
        for obj in net_objects:
            if isinstance(obj, (SpatialNeuron, SpatialStateUpdater)):
                raise NotImplementedError(
                    'Brian2GeNN does not support multicompartmental neurons')
            if not isinstance(obj, (
            NeuronGroup, PoissonGroup, SpikeGeneratorGroup, Synapses,
            SpikeMonitor, PopulationRateMonitor, StateMonitor,
            StateUpdater, SynapsesStateUpdater, Resetter,
            Thresholder, SynapticPathway, CodeRunner)):
                raise NotImplementedError(
                    "Brian2GeNN does not support objects of type "
                    "'%s'" % obj.__class__.__name__)
            # We only support run_regularly and "constant over dt"
            # subexpressions for neurons
            if (isinstance(obj, SubexpressionUpdater) and
                    not isinstance(obj.group, NeuronGroup)):
                raise NotImplementedError(
                    'Subexpressions with the flag "constant over dt" are only '
                    'supported for NeuronGroup (not for objects of type '
                    '"%s").' % obj.group.__class__.__name__
                )

        self.dtDef = 'model.setDT(' + repr(float(defaultclock.dt)) + ');'

        # Process groups
        self.process_neuron_groups(neuron_groups, objects)
        self.process_poisson_groups(objects, poisson_groups)
        self.process_spikegenerators(spikegenerator_groups)
        self.process_synapses(synapse_groups, objects)
        # Process monitors
        self.process_spike_monitors(spike_monitors)
        self.process_rate_monitors(rate_monitors)
        self.process_state_monitors(directory, state_monitors, writer)

        # Turn anonymous namespaces into named namespaces to avoid
        # issues when cpp files are included
        for code_object in itertools.chain(self.code_objects.values(),
                                           self.max_row_length_code_objects.values()):
            cpp_code = getattr(code_object.code, 'cpp_file', code_object.code)
            if 'namespace {' in cpp_code:
                cpp_code = cpp_code.replace('namespace {', f'namespace {code_object.name} {{')
                cpp_code = cpp_code.replace('using namespace brian;',
                                            f'using namespace brian;\nusing namespace {code_object.name};')
                if hasattr(code_object.code, 'cpp_file'):
                    code_object.code.cpp_file = cpp_code
            else:
                code_object.code = cpp_code
        # Write files from templates
        # Create an empty network.h file, this allows us to use Brian2's
        # objects.cpp template unchanged
        writer.write('network.*', GeNNUserCodeObject.templater.network(None, None))
        self.header_files.add('network.h')

        self.generate_objects_source(arange_arrays, self.net,
                                     static_array_specs,
                                     synapse_groups, writer)
        self.copy_source_files(writer, directory)

        # Rename randomkit.c so that it gets compiled by an explicit rule in
        # GeNN's makefile template, otherwise optimization flags will not be
        # used.
        randomkit_dir = os.path.join(directory, 'brianlib', 'randomkit')
        shutil.move(os.path.join(randomkit_dir, 'randomkit.c'),
                    os.path.join(randomkit_dir, 'randomkit.cc'))
        self.generate_code_objects(writer)
        self.generate_max_row_length_code_objects(writer)
        self.generate_model_source(writer, main_lines, use_GPU)
        self.generate_main_source(writer, main_lines)
        self.generate_engine_source(writer, objects)
        self.generate_makefile(directory, use_GPU)

        # Compile and run
        if compile:
            try:
                self.compile_source(debug, directory, use_GPU)
            except CalledProcessError as ex:
                raise RuntimeError(('Project compilation failed (Command {cmd} '
                                    'failed with error code {returncode}).\n'
                                    'See the output above (if any) for more '
                                    'details.').format(cmd=ex.cmd,
                                                       returncode=ex.returncode)
                                   )
        if run:
            try:
                self.run(directory, use_GPU, with_output)
            except CalledProcessError as ex:
                if ex.returncode == 222:
                    raise NotImplementedError('GeNN does not support multiple '
                                              'synapses per neuron pair (use '
                                              'multiple Synapses objects).')
                else:
                    raise RuntimeError(('Project run failed (Command {cmd} '
                                        'failed with error code {returncode}).\n'
                                        'See the output above (if any) for more '
                                        'details.').format(cmd=ex.cmd,
                                                           returncode=ex.returncode)
                                       )

    def generate_code_objects(self, writer):
        # Generate data for non-constant values
        code_object_defs = defaultdict(list)
        for codeobj in self.code_objects.values():
            lines = []
            for k, v in codeobj.variables.items():
                if isinstance(v, ArrayVariable):
                    try:
                        if isinstance(v, DynamicArrayVariable):
                            if get_var_ndim(v) == 1:
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
                            lines.append(f'const int _num{k} = {v.size};')
                    except TypeError:
                        pass
            for line in lines:
                # Sometimes an array is referred to by to different keys in our
                # dictionary -- make sure to never add a line twice
                if not line in code_object_defs[codeobj.name]:
                    code_object_defs[codeobj.name].append(line)
        # Generate the code objects
        for codeobj in self.code_objects.values():
            ns = codeobj.variables
            # TODO: fix these freeze/CONSTANTS hacks somehow - they work but not elegant.
            if ((codeobj.template_name not in ['stateupdate', 'threshold',
                                               'reset', 'synapses']) or
                    ('_run_regularly_' in codeobj.name)):
                if isinstance(codeobj.code, MultiTemplate):
                    code = freeze(codeobj.code.cpp_file, ns)
                    code = code.replace('%CONSTANTS%', '\n'.join(
                        code_object_defs[codeobj.name]))
                    code = '#include "objects.h"\n' + code

                    writer.write('code_objects/' + codeobj.name + '.cpp', code)
                    self.source_files.add(
                        'code_objects/' + codeobj.name + '.cpp')
                    writer.write('code_objects/' + codeobj.name + '.h',
                                 codeobj.code.h_file)
                    self.header_files.add(
                        'code_objects/' + codeobj.name + '.h')

    def generate_max_row_length_code_objects(self, writer):
        # Generate data for non-constant values
        code_object_defs = defaultdict(set)
        for codeobj in self.max_row_length_code_objects.values():
            for k, v in codeobj.variables.items():
                if isinstance(v, ArrayVariable):
                    try:
                        if isinstance(v, DynamicArrayVariable):
                            if get_var_ndim(v) == 1:
                                dyn_array_name = self.dynamic_arrays[v]
                                array_name = self.arrays[v]
                                # do the const stuff
                                line = '{c_type}* const {array_name} = &{dyn_array_name}[0];'
                                line = line.format(c_type=c_data_type(v.dtype),
                                                   array_name=array_name,
                                                   dyn_array_name=dyn_array_name)
                                code_object_defs[codeobj.name].add(line)
                                line = 'const int _num{k} = {dyn_array_name}.size();'
                                line = line.format(k=k,
                                                   dyn_array_name=dyn_array_name)
                                code_object_defs[codeobj.name].add(line)
                        else:
                            array_name = self.arrays[v]
                            line = '{c_type} {array_name}[{size}];'
                            line = line.format(c_type=c_data_type(v.dtype),
                                               array_name=array_name,
                                               size=v.size)
                            code_object_defs[codeobj.name].add(f'const int _num{k} = {v.size};')
                    except TypeError:
                        pass

        for codeobj in self.max_row_length_code_objects.values():
            ns = codeobj.variables
            # TODO: fix these freeze/CONSTANTS hacks somehow - they work but not elegant.
            code = freeze(codeobj.code, ns)
            code = code.replace('%CONSTANTS%', '\n'.join(
                        code_object_defs[codeobj.name]))
            writer.write('code_objects/' + codeobj.name + '.cpp', code)



    def run(self, directory, use_GPU, with_output):
        gpu_arg = "1" if use_GPU else "0"
        if gpu_arg == "1":
            where = 'on GPU'
        else:
            where = 'on CPU'
        print('executing genn binary %s ...' % where)

        pref_vars = prefs['devices.cpp_standalone.run_environment_variables']
        for key, value in itertools.chain(pref_vars.items(),
                                          self.run_environment_variables.items()):
            if key in os.environ and os.environ[key] != value:
                logger.info('Overwriting environment variable '
                            '"{key}"'.format(key=key),
                            name_suffix='overwritten_env_var', once=True)
            os.environ[key] = value

        with std_silent(with_output):
            if os.sys.platform == 'win32':
                cmd = directory + "\\main_Release.exe test " + str(
                    self.run_duration)
                check_call(cmd, cwd=directory)
            else:
                # print ["./main", "test", str(self.run_duration), gpu_arg]
                check_call(["./main", "test", str(self.run_duration)],
                           cwd=directory)
        self.has_been_run = True
        with open(os.path.join(directory, 'results/last_run_info.txt')) as f:
            last_run_info = f.read()
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
        if prefs.devices.genn.path is not None:
            genn_path = prefs.devices.genn.path
            logger.debug('Using GeNN path from preference: '
                         '"{}"'.format(genn_path))
        elif 'GENN_PATH' in os.environ:
            genn_path = os.environ['GENN_PATH']
            logger.debug('Using GeNN path from environment variable: '
                         '"{}"'.format(genn_path))
        else:
            # Find genn-buildmodel
            genn_bin = (find_executable("genn-buildmodel.bat")
                        if os.sys.platform == 'win32'
                        else find_executable("genn-buildmodel.sh"))

            if genn_bin is None:
                raise RuntimeError('Add GeNN\'s bin directory to the path '
                                   'or set the devices.genn.path preference.')

            # Remove genn-buildmodel from path, navigate up a directory and normalize
            genn_path = os.path.normpath(os.path.join(os.path.dirname(genn_bin), ".."))
            logger.debug('Using GeNN path determined from path: '
                         '"{}"'.format(genn_path))

        # Check for GeNN compatibility
        genn_version = None
        version_file = os.path.join(genn_path, 'version.txt')
        if os.path.exists(version_file):
            try:
                with open(version_file) as f:
                    genn_version = parse_version(f.read().strip())
                    logger.debug('GeNN version: %s' % genn_version)
            except OSError as ex:
                logger.debug('Getting version from %s/version.txt '
                             'failed: %s' % (genn_path, str(ex)))

        if genn_version is None or not genn_version >= parse_version('4.2.1'):
            raise RuntimeError('Brian2GeNN requires GeNN 4.2.1 or later. '
                               'Please upgrade your GeNN version.')

        env = os.environ.copy()
        if use_GPU:
            if prefs.devices.genn.cuda_backend.cuda_path is not None:
                cuda_path = prefs.devices.genn.cuda_backend.cuda_path
                env['CUDA_PATH'] = cuda_path
                logger.debug('Using CUDA path from preference: '
                             '"{}"'.format(cuda_path))
            elif 'CUDA_PATH' in env:
                cuda_path = env['CUDA_PATH']
                logger.debug('Using CUDA path from environment variable: '
                             '"{}"'.format(cuda_path))
            else:
                raise RuntimeError('Set the CUDA_PATH environment variable or '
                                   'the devices.genn.cuda_backend.cuda_path preference.')

        with std_silent(debug):
            if os.sys.platform == 'win32':
                # Make sure that all environment variables are upper case
                env = {k.upper() : v for k, v in env.items()}

                # If there is vcvars command to call, start cmd with that
                cmd = ''
                msvc_env, vcvars_cmd = get_msvc_env()
                if vcvars_cmd:
                    cmd += vcvars_cmd + ' && '
                # Otherwise, update environment, again ensuring
                # that all variables are upper case
                else:
                    env.update({k.upper() : v for k, v in msvc_env.items()})

                # Add start of call to genn-buildmodel
                buildmodel_cmd = os.path.join(genn_path, 'bin',
                                              'genn-buildmodel.bat')
                cmd += buildmodel_cmd + ' -s'

                # If we're not using CPU, add CPU option
                if not use_GPU:
                    cmd += ' -c'

                # Add include directories
                # **NOTE** on windows semicolons are used to seperate multiple include paths
                # **HACK** argument list syntax to check_call doesn't support quoting arguments to batch
                # files so we have to build argument string manually(https://bugs.python.org/issue23862)
                wdir = os.getcwd()
                cmd += ' -i "{};{};{}"'.format(wdir, os.path.join(wdir, directory),
                                           os.path.join(wdir, directory, 'brianlib','randomkit'))
                cmd += ' magicnetwork_model.cpp'

                # Add call to build generated code
                cmd += ' && msbuild /m /verbosity:minimal /p:Configuration=Release "' + os.path.join(wdir, directory, 'magicnetwork_model_CODE', 'runner.vcxproj') + '"'

                # Add call to build executable
                cmd += ' && msbuild /m /verbosity:minimal /p:Configuration=Release "' + os.path.join(wdir, directory, 'project.vcxproj') + '"'

                # Run combined command
                # **NOTE** because vcvars MODIFIED environment,
                # making seperate check_calls doesn't work
                check_call(cmd, cwd=directory, env=env)
            else:
                if prefs['codegen.cpp.extra_link_args']:
                    # declare the link flags as an environment variable so that GeNN's
                    # generateALL can pick it up
                    env['LDFLAGS'] = ' '.join(prefs['codegen.cpp.extra_link_args'])

                buildmodel_cmd = os.path.join(genn_path, 'bin', 'genn-buildmodel.sh')
                args = [buildmodel_cmd]
                if not use_GPU:
                    args += ['-c']
                wdir= os.getcwd()
                inc_path= wdir;
                inc_path+= ':'+os.path.join(wdir, directory)
                inc_path+= ':'+os.path.join(wdir, directory, 'brianlib','randomkit')
                args += ['-i', inc_path]
                args += ['magicnetwork_model.cpp']
                print(args)
                check_call(args, cwd=directory, env=env)
                call(["make", "clean"], cwd=directory, env=env)
                check_call(["make"], cwd=directory, env=env)

    def add_parameter(self, model, varname, variable):
        model.parameters.append(varname)
        model.pvalue.append(CPPNodeRenderer().render_expr(repr(variable.value)))

    def add_array_variable(self, model, varname, variable):
        if variable.scalar:
            model.shared_variables.append(varname)
            model.shared_variabletypes.append(c_data_type(variable.dtype))
        else:
            model.variables.append(varname)
            model.variabletypes.append(c_data_type(variable.dtype))
            model.variablescope[varname] = 'brian'

    def add_array_variables(self, model, owner):
        for varname, variable in owner.variables.items():
            if varname in ['_spikespace', 't', 'dt']:
                pass
            elif getattr(variable.owner, 'name', None) != owner.name:
                pass
            elif isinstance(variable, ArrayVariable):
                self.add_array_variable(model, varname, variable)

    def process_poisson_groups(self, objects, poisson_groups):
        for obj in poisson_groups:
            # throw error if events other than spikes are used
            event_keys = list(obj.events.keys())
            if (len(event_keys) > 1
                or (len(event_keys) == 1 and event_keys[0] != 'spike')):
                raise NotImplementedError(
                    'Brian2GeNN does not support events that are not spikes')

            # Extract the variables
            neuron_model = neuronModel()
            neuron_model.name = obj.name
            neuron_model.clock = obj.clock
            neuron_model.N = obj.N
            self.add_array_variables(neuron_model, obj)
            support_lines = []
            codeobj = obj.thresholder['spike'].codeobj
            lines = neuron_model.thresh_cond_lines
            for k, v in codeobj.variables.items():
                if k != 'dt' and isinstance(v, Constant):
                    if k not in neuron_model.parameters:
                        self.add_parameter(neuron_model, k, v)
                code = codeobj.code.cpp_file

            code = self.fix_random_generators(neuron_model, code)
            code = decorate(code, neuron_model.variables,
                            neuron_model.shared_variables,
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
            event_keys = list(obj.events.keys())
            if len(event_keys) > 1 or (len(event_keys) == 1 and event_keys[0] != 'spike'):
                raise NotImplementedError(
                    'Brian2GeNN does not support events that are not spikes')
            # Extract the variables
            neuron_model = neuronModel()
            neuron_model.name = obj.name
            neuron_model.clock = obj.clock
            neuron_model.N = obj.N
            self.add_array_variables(neuron_model, obj)

            # We have previously only created "dummy code objects" for the
            # state update, threshold, and reset of a NeuronGroup. We will now
            # generate a single code object for all of them, adding the
            # threshold calculation code to the end of the state update. When
            # using subexpressions, the threshold condition code could consist
            # of multiple lines, and GeNN only supports a threshold condition
            # that is directly used as an if condition. We therefore store the
            # result in a boolean variable and only pass this variable as the
            # threshold condition to GeNN.
            # It is also important that stateupdate/threshold share the same
            # code object with the reset, as in GeNN both codes have the same
            # support code. If they used two separate code objects, adding the
            # two support codes might lead to duplicate definitions of
            # functions.
            combined_abstract_code = {'stateupdate': [], 'reset': [],
                                      'subexpression_update': [],
                                      'poisson_input': []}
            combined_variables = {}
            combined_variable_indices = defaultdict(lambda: '_idx')
            combined_override_conditional_write = set()
            has_thresholder = False

            stateupdater_name = None
            slot_mapping = {StateUpdater: 'stateupdate',
                            Thresholder: 'stateupdate',
                            Resetter: 'reset',
                            SubexpressionUpdater: 'subexpression_update'}
            for klass, code_slot in slot_mapping.items():
                codeobj = None
                for contained_obj in obj.contained_objects:
                    if isinstance(contained_obj, klass):
                        codeobj = contained_obj.codeobj
                        if klass is StateUpdater:
                            stateupdater_name = contained_obj.name
                        break
                if codeobj is not None:
                    combined_abstract_code[code_slot] += [
                        codeobj.abstract_code[None]]
                    combined_variables.update(codeobj.variables)
                    combined_variable_indices.update(codeobj.variable_indices)
                    # The resetter includes "not_refractory" as an override_conditional_write
                    # variable, meaning that it removes the write-protection based on that
                    # variable that would otherwise apply to "unless refractory" variables,
                    # e.g. the membrane potential. This is not strictly necessary, it will just
                    # introduce an unnecessary check, because a neuron that spiked is by
                    # definition not in its refractory period. However, if we included it as
                    # a override_conditional_write variable for the whole code object here,
                    # this would apply also to the state updater, and therefore
                    # remove the write-protection from "unless refractory" variables in the
                    # state update code.
                    if klass is not Resetter:
                        combined_override_conditional_write.update(
                            codeobj.override_conditional_write)
                    if klass is Thresholder:
                        has_thresholder = True

            if has_thresholder:
                neuron_model.thresh_cond_lines = '_cond'
            else:
                neuron_model.thresh_cond_lines = '0'

            if obj._refractory is not False:
                combined_abstract_code['reset'] += ['lastspike = t',
                                                    'not_refractory = False']

            # Find PoissonInputs targetting this NeuronGroup
            poisson_inputs = [o for o in objects.values()
                              if isinstance(o, PoissonInput) and
                                 o.group.name == obj.name]

            for poisson_input in poisson_inputs:
                if poisson_input.when != 'synapses':
                    raise NotImplementedError('Brian2GeNN does not support '
                                              'changing the scheduling slot '
                                              'of PoissonInput objects.')
                codeobj = poisson_input.codeobj
                combined_abstract_code['poisson_input'] += [codeobj.abstract_code[None]]
                combined_variables.update(codeobj.variables)
                combined_variable_indices.update(codeobj.variable_indices)

            for code_block in combined_abstract_code.keys():
                combined_abstract_code[code_block] = '\n'.join(combined_abstract_code[code_block])

            if any(len(ac) for ac in combined_abstract_code.values()):
                assert stateupdater_name, 'No StateUpdater found in object.'
                codeobj = super().code_object(obj, stateupdater_name,
                                                              combined_abstract_code,
                                                              combined_variables.copy(),
                                                              'neuron_code',
                                                              combined_variable_indices,
                                                              codeobj_class=GeNNCodeObject,
                                                              override_conditional_write=combined_override_conditional_write,
                                                              )

                # Remove the code object from the code_objects dictionary, we
                # take care of it manually and do not want it to be generated as
                # part of `generate_code_objects`.
                del self.code_objects[codeobj.name]

                for k, v in codeobj.variables.items():
                    if k != 'dt' and isinstance(v, Constant):
                        if k not in neuron_model.parameters:
                            self.add_parameter(neuron_model, k, v)

                update_code = codeobj.code.stateupdate_code
                reset_code = codeobj.code.reset_code
                for code, lines in [(update_code, neuron_model.code_lines),
                                    (reset_code, neuron_model.reset_code_lines)]:
                    code = self.fix_random_generators(neuron_model, code)
                    code = decorate(code, neuron_model.variables,
                                    neuron_model.shared_variables,
                                    neuron_model.parameters).strip()
                    lines.append(code)
                support_code = stringify(codeobj.code.h_file)
                neuron_model.support_code_lines = support_code
            self.neuron_models.append(neuron_model)
            self.groupDict[neuron_model.name] = neuron_model

    def process_spikegenerators(self, spikegenerator_groups):
        for obj in spikegenerator_groups:
            spikegenerator_model = spikegeneratorModel()
            spikegenerator_model.name = obj.name
            spikegenerator_model.codeobject_name = obj.codeobj.name
            spikegenerator_model.N = obj.N
            self.spikegenerator_models.append(spikegenerator_model)

    def process_synapses(self, synapse_groups, objects):
        for obj in synapse_groups:
            synapse_model = synapseModel()
            synapse_model.name = obj.name
            if isinstance(obj.source, Synapses) or isinstance(obj.target, Synapses):
                raise NotImplementedError('Brian2GeNN does not support '
                                          'Synapses objects as source or '
                                          'target of Synapses objects.')
            if isinstance(obj.source, Subgroup):
                synapse_model.srcname = obj.source.source.name
                synapse_model.srcN = obj.source.source.variables['N'].get_value()
            else:
                synapse_model.srcname = obj.source.name
                synapse_model.srcN = obj.source.variables['N'].get_value()
            if isinstance(obj.target, Subgroup):
                synapse_model.trgname = obj.target.source.name
                synapse_model.trgN = obj.target.source.variables['N'].get_value()
            else:
                synapse_model.trgname = obj.target.name
                synapse_model.trgN = obj.target.variables['N'].get_value()
            synapse_model.connectivity = prefs.devices.genn.connectivity
            self.connectivityDict[obj.name] = synapse_model.connectivity

            for pathway in obj._synaptic_updaters:
                if pathway not in ['pre', 'post']:
                    raise NotImplementedError("brian2genn only supports a "
                                              "single synaptic pre and post "
                                              "pathway, cannot use pathway "
                                              "'%s'." % pathway)

            for pathway in ['pre', 'post']:
                if hasattr(obj, pathway):
                    codeobj = getattr(obj, pathway).codeobj
                    # A little hack to support "write-protection" for refractory
                    # variables -- brian2genn currently requires that
                    # post-synaptic variables end with "_post"
                    if pathway == 'pre' and 'not_refractory' in codeobj.variables:
                        codeobj.variables['not_refractory_post'] = \
                        codeobj.variables['not_refractory']
                        codeobj.variable_indices['not_refractory_post'] = \
                        codeobj.variable_indices['not_refractory']
                        del codeobj.variables['not_refractory']
                        del codeobj.variable_indices['not_refractory']
                    self.collect_synapses_variables(synapse_model, pathway,
                                                    codeobj)
                    if pathway == 'pre':
                        # Use the stored scalar delay (if any) for these synapses
                        synapse_model.delay = int(
                            self.delays.get(obj.name,
                                            0.0) / defaultclock.dt_ + 0.5)
                    code = codeobj.code.cpp_file
                    code_lines = [line.strip() for line in code.split('\n')]
                    new_code_lines = []
                    if pathway == 'pre':
                        for line in code_lines:
                            if line.startswith('addtoinSyn'):
                                if synapse_model.connectivity == 'SPARSE':
                                    line = line.replace('_hidden_weightmatrix*',
                                                        '')
                                    line = line.replace(
                                        '_hidden_weightmatrix *', '')
                            new_code_lines.append(line)
                        code = '\n'.join(new_code_lines)

                    self.fix_synapses_code(synapse_model, pathway, codeobj,
                                           code)

            if obj.state_updater is not None:
                codeobj = obj.state_updater.codeobj
                code = codeobj.code.cpp_file
                self.collect_synapses_variables(synapse_model, 'dynamics',
                                                codeobj)
                self.fix_synapses_code(synapse_model, 'dynamics', codeobj,
                                       code)

            synapse_model.summed_variables = [ s for s in objects if s.startswith(obj.name+'_summed_variable')]
            if len(synapse_model.summed_variables) > 0 and hasattr(obj, '_genn_post_write_var'):
                raise NotImplementedError("brian2genn only supports a "
                                          "either a single synaptic output variable "
                                          "or a single summed variable per Synapses group.")
            if len(synapse_model.summed_variables) > 0 and isinstance(obj.target,Subgroup):
                raise NotImplementedError("brian2genn does not support summed variables "
                                          "when the target is a Subgroup.")
            if len(synapse_model.summed_variables) > 1:
                 raise NotImplementedError("brian2genn only supports a "
                                          "single summed variable per Synapses group.")
            if hasattr(obj, '_genn_post_write_var'):
                synapse_model.postSyntoCurrent = '0; $(' + obj._genn_post_write_var.replace(
                    '_post', '') + ') += $(inSyn); $(inSyn)= 0'
            else:
                if len(synapse_model.summed_variables) > 0:
                    summed_variable_updater= objects.get(synapse_model.summed_variables[0], None)
                    if obj.target != summed_variable_updater.target:
                        raise NotImplementedError("brian2genn only supports summed "
                                          "variables that target the post-synaptic neuron group of the Synapses the variable is defined in.")
                    synapse_model.postSyntoCurrent = '0; $(' + summed_variable_updater.target_var.name + ') = $(inSyn); $(inSyn)= 0'
                    # also add the inSyn updating code to the synapse dynamics code
                    addVar = summed_variable_updater.abstract_code.replace('_synaptic_var = ', '').replace('\n', '').replace(' ', '')
                    codeobj = summed_variable_updater.codeobj
                    code_generator = GeNNCodeGenerator(codeobj.variables, codeobj.variable_indices, codeobj.owner, None,
                                                       GeNNCodeObject, codeobj.name, None)
                    addVar = code_generator.translate_expression(addVar)
                    kwds = code_generator.determine_keywords()
                    identifiers = get_identifiers(addVar)
                    for k, v in codeobj.variables.items():
                        if k in ['_spikespace', 't', 'dt'] or k not in identifiers:
                            pass
                        else:
                            if '_pre' not in k and '_post' not in k:
                                if isinstance(v, Constant):
                                    if k not in synapse_model.parameters:
                                        self.add_parameter(synapse_model, k, v)
                                elif isinstance(v, ArrayVariable):
                                    if k not in synapse_model.variables:
                                        self.add_array_variable(synapse_model, k, v)
                            addVar= addVar.replace(k,'$('+k+')')
                    code= '\\n\\\n $(addToInSyn,'+addVar+');\\n'
                    synapse_model.main_code_lines['dynamics'] += code
                    #quick and dirty test to avoid adding the same support code twice
                    support_code = stringify('\n'.join(kwds['support_code_lines']))
                    if support_code not in synapse_model.support_code_lines['dynamics']:
                        synapse_model.support_code_lines['dynamics'] += support_code
                else:
                    synapse_model.postSyntoCurrent = '0'
            self.synapse_models.append(synapse_model)
            self.groupDict[synapse_model.name] = synapse_model

    def collect_synapses_variables(self, synapse_model, pathway, codeobj):
        identifiers = set()
        for code in codeobj.code.values():
            identifiers |= get_identifiers(code)
        indices = codeobj.variable_indices
        for k, v in codeobj.variables.items():
            if k in ['_spikespace', 't', 'dt'] or k not in identifiers:
                pass
            elif isinstance(v, Constant):
                if k not in synapse_model.parameters:
                    self.add_parameter(synapse_model, k, v)
            elif isinstance(v, ArrayVariable):
                if indices[k] == '_idx':
                    if k not in synapse_model.variables:
                        self.add_array_variable(synapse_model, k, v)
                elif indices[k] == '0':
                    if k not in synapse_model.shared_variables:
                        self.add_array_variable(synapse_model, k, v)
                else:
                    index = indices[k]
                    if (pathway in ['pre', 'post'] and
                                index == f'_{pathway}synaptic_idx'):
                        raise NotImplementedError('brian2genn does not support '
                                                  'references to {pathway}-'
                                                  'synaptic variables in '
                                                  'on_{pathway} '
                                                  'statements.'.format(
                            pathway=pathway))
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
                           synapse_model.shared_variables,
                           synapse_model.parameters, False).strip()
        thecode = decorate(thecode, synapse_model.external_variables, [],
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
            sm.codeobject_name = obj.codeobj.name
            if (hasattr(obj, 'when')):
                if (not obj.when in ['end', 'thresholds']):
                    # GeNN always records in the end slot but this should
                    # almost never make a difference and we therefore do not
                    # raise a warning if the SpikeMonitor records in the default
                    # thresholds slot. We do raise a NotImplementedError if the
                    # user manually changed the time slot to something else --
                    # there was probably a reason for doing it.
                    raise NotImplementedError(
                        "Spike monitor {!s} has 'when' property '{!s}' which "
                        "is not supported in GeNN, defaulting to 'end'.".format(
                            sm.name, obj.when))
            src = obj.source
            if isinstance(src, Subgroup):
                src = src.source
            sm.neuronGroup = src.name
            if isinstance(src, SpikeGeneratorGroup):
                sm.notSpikeGeneratorGroup = False
            self.spike_monitor_models.append(sm)

            # ------------------------------------------------------------------------------
            # Process rate monitors

    def process_rate_monitors(self, rate_monitors):
        for obj in rate_monitors:
            sm = rateMonitorModel()
            sm.name = obj.name
            sm.codeobject_name = obj.codeobj.name
            if obj.when != 'end':
                logger.warn("Rate monitor {!s} has 'when' property '{!s}' which"
                            "is not supported in GeNN, defaulting to"
                            "'end'.".format(sm.name, obj.when))
            src = obj.source
            if isinstance(src, Subgroup):
                src = src.source
            sm.neuronGroup = src.name
            if isinstance(src, SpikeGeneratorGroup):
                sm.notSpikeGeneratorGroup = False
            self.rate_monitor_models.append(sm)

    def process_state_monitors(self, directory, state_monitors, writer):
        for obj in state_monitors:
            sm = stateMonitorModel()
            sm.name = obj.name
            sm.codeobject_name = obj.codeobj.name
            sm.order = obj.order
            src = obj.source
            if isinstance(src, Subgroup):
                src = src.source
            sm.monitored = src.name
            sm.src = src
            sm.when = obj.when
            if sm.when not in ['start', 'end']:
                logger.warn("State monitor {!s} has 'when' property '{!s}'"
                            "which is not supported in GeNN, defaulting to"
                            "'end'.".format(sm.name, sm.when))
                sm.when = 'end'
            if isinstance(src, Synapses):
                sm.isSynaptic = True
                neuron_src = src.source
                # in brian2genn, we need the size of the entire pre-synaptic neuron population, not a sub-group size
                if isinstance(neuron_src, Subgroup):
                    neuron_src = neuron_src.source
                sm.srcN = neuron_src.variables['N'].get_value()
                neuron_trg = src.target
                # in brian2genn, we need the size of the entire post-synaptic neuron population, not a sub-group size
                if isinstance(neuron_trg, Subgroup):
                    neuron_trg = neuron_trg.source
                sm.trgN = neuron_trg.variables['N'].get_value()
                sm.connectivity = self.connectivityDict[src.name]
            else:
                sm.isSynaptic = False
                sm.N = src.variables['N'].get_value()
            for varname in obj.record_variables:
                if src.variables[varname] in defaultclock.variables.values():
                    raise NotImplementedError('Recording the time t or the '
                                              'timestep dt is currently not '
                                              'supported in Brian2GeNN')
                if isinstance(src.variables[varname], Subexpression):
                    extract_source_variables(src.variables, varname,
                                             sm.variables)
                elif isinstance(src.variables[varname], Constant):
                    logger.warn(
                        "variable '%s' is a constant - not monitoring" % varname)
                elif varname not in self.groupDict[sm.monitored].variables:
                    # Check that the variable is also not updated by any run_regularly operation
                    run_regularly_objects = {o.name: o for o in self.net_objects
                                             if '_run_regularly' in o.name}
                    updated = False
                    for codeobj_name, read_write in self.run_regularly_read_write.items():
                        if (
                                varname in read_write['write'] and
                                run_regularly_objects[codeobj_name].owner.name == sm.monitored
                        ):
                            updated = True
                            break

                    if updated:
                        sm.variables.append(varname)
                    else:
                        raise NotImplementedError("variable '%s' is unused - cannot monitor it" % varname)
                else:
                    sm.variables.append(varname)
            if obj.clock.name != 'defaultclock':
                obj_dt = obj.clock.dt_
                source_dt = src.dt_[:]
                if obj_dt < source_dt:
                    raise NotImplementedError(
                        'Brian2GeNN does not support StateMonitors '
                        'with a dt smaller than the dt of the '
                        'monitored object')
                dt_mismatch = abs(((obj_dt + source_dt / 2) % source_dt) - source_dt / 2)
                if dt_mismatch > 1e-4 * source_dt:
                    raise NotImplementedError(
                        'Brian2GeNN does not support StateMonitors '
                        'with a dt that is not a multiple of the dt of the '
                        'monitored object.')
                sm.step = int(obj_dt / source_dt + 0.5)

            self.state_monitor_models.append(sm)

    def consolidate_pull_operations(self, run_regularly_operations):
        models_start = defaultdict(list)
        models_end = defaultdict(list)
        for sm in self.state_monitor_models:
            if sm.when == 'start':
                for varname in sm.variables:
                    # Do not pull variables that are only updated in run_regularly
                    if varname in self.groupDict[sm.monitored].variables:
                        models_start[f'{varname}{sm.monitored}'].append(sm.step)
            else:
                for varname in sm.variables:
                    if varname in self.groupDict[sm.monitored].variables:
                        models_end[f'{varname}{sm.monitored}'].append(sm.step)
        for op in run_regularly_operations:
            for varname in op['read']:
                if varname not in ['t', 'dt']:
                    owner_name = op['owner'].variables[varname].owner.name
                    models_start[f'{varname}{owner_name}'].append(op['step'])
        # Shortcut: If a state is pulled on every turn, no need to list all steps
        models_start = {key: [1] if 1 in val else sorted(set(val))
                        for key, val in models_start.items()}
        models_end = {key: [1] if 1 in val else sorted(set(val))
                      for key, val in models_end.items()}
        # Shortcut: If start or end pulls on every turn, pulling on start is enough.
        for key, val in models_start.items():
            if (key in models_end) and (val[0] == 1 or models_end[key][0] == 1):
                models_end.pop(key)
                models_start[key] = [1]
        return models_start, models_end

    def generate_model_source(self, writer, main_lines, use_GPU):
        synapses_classes_tmp = CPPStandaloneCodeObject.templater.synapses_classes(None, None)
        writer.write('synapses_classes.*', synapses_classes_tmp)
        default_dtype = prefs.core.default_float_dtype
        if default_dtype == numpy.float32:
            precision = 'GENN_FLOAT'
        elif default_dtype == numpy.float64:
            precision = 'GENN_DOUBLE'
        else:
            raise NotImplementedError("GeNN does not support default dtype "
                                      "'{}'".format(default_dtype.__name__))
        dry_main_lines= []
        for line in main_lines:
            if ('_synapses_create_' not in line) and ('monitor' not in line):
                dry_main_lines.append(line)
        codeobj_inc= []
        for codeobj in self.code_objects.values():
            if ('group_variable' in codeobj.name):
                codeobj_inc.append('#include "code_objects/'+codeobj.name+'.cpp"')
        model_tmp = GeNNCodeObject.templater.model(None, None,
                                                   use_GPU=use_GPU,
                                                   code_lines=self.code_lines,
                                                   neuron_models=self.neuron_models,
                                                   spikegenerator_models=self.spikegenerator_models,
                                                   synapse_models=self.synapse_models,
                                                   main_lines=dry_main_lines,
                                                   max_row_length_include= self.max_row_length_include,
                                                   max_row_length_run_calls=self.max_row_length_run_calls,
                                                   max_row_length_synapses=self.max_row_length_synapses,
                                                   codeobj_inc=codeobj_inc,
                                                   dtDef=self.dtDef,
                                                   profiled=self.kernel_timings,
                                                   prefs=prefs,
                                                   precision=precision,
                                                   header_files=prefs['codegen.cpp.headers']
                                                   )
        writer.write('magicnetwork_model.cpp', model_tmp)

    def generate_main_source(self, writer, main_lines):
        header_files = sorted(self.header_files) + prefs['codegen.cpp.headers']
        runner_tmp = GeNNCodeObject.templater.main(None, None,
                                                   code_lines=self.code_lines,
                                                   neuron_models=self.neuron_models,
                                                   synapse_models=self.synapse_models,
                                                   main_lines=main_lines,
                                                   header_files=header_files,
                                                   source_files=sorted(self.source_files),
                                                   profiled=self.kernel_timings,
                                                   )
        writer.write('main.*', runner_tmp)

    def generate_engine_source(self, writer, objects):
        maximum_run_time = self._maximum_run_time
        if maximum_run_time is not None:
            maximum_run_time = float(maximum_run_time)
        run_regularly_objects = [o for name, o in objects.items()
                                 if '_run_regularly' in name]
        run_regularly_operations = []
        for run_reg in run_regularly_objects:
            # Figure out after how many steps the operation should be executed
            if run_reg.when != 'start':
                raise NotImplementedError(
                    'Brian2GeNN does not support changing '
                    'the scheduling slot for "run_regularly" '
                    'operations.')
            run_regularly_dt = run_reg.clock.dt_
            group_dt = run_reg.group.dt_[:]
            if run_regularly_dt < group_dt:
                raise NotImplementedError(
                    'Brian2GeNN does not support run_regularly '
                    'operations with a dt smaller than the dt '
                    'used by the group.')
            dt_mismatch = abs(((run_regularly_dt + group_dt / 2) % group_dt) - group_dt / 2)
            if dt_mismatch > 1e-4 * group_dt:
                raise NotImplementedError(
                    'Brian2GeNN does not support run_regularly '
                    'operations where the dt is not a multiple of '
                    'the dt used by the group.')
            step_value = int(run_regularly_dt / group_dt + 0.5)
            codeobj_read_write = self.run_regularly_read_write[run_reg.codeobj.name]
            op = {'name': run_reg.name,
                  'order': run_reg.order,
                  'codeobj': run_reg.codeobj,
                  'owner': run_reg.group,
                  'read': codeobj_read_write['read'],
                  'write': codeobj_read_write['write'],
                  'step': step_value,
                  'isSynaptic': False}
            if isinstance(run_reg.group, Synapses):
                op['isSynaptic'] = True
                op['srcN'] = run_reg.group.source.variables['N'].get_value()
                op['trgN'] = run_reg.group.target.variables['N'].get_value()
                op['connectivity'] = self.connectivityDict[run_reg.group.name]
            run_regularly_operations.append(op)

        # StateMonitors and run_regularly operations are both executed in the "start"
        # slot. Their order of execution can matter, so we provide a list which sorts
        # them by their order attribute. For convenient use in the template, the list
        # stores tuples of a boolean and the object, where the boolean states whether
        # the object is a stateMonitorModel.
        run_reg_state_monitor_operations = ([(run_reg['order'], run_reg['name'], False, run_reg)
                                             for run_reg in run_regularly_operations] +
                                            [(sm.order, sm.name, True, sm)
                                             for sm in self.state_monitor_models]
                                            )
        run_reg_state_monitor_operations = [(is_state_mon, obj)
                                            for _, _, is_state_mon, obj
                                            in sorted(run_reg_state_monitor_operations)]
        vars_to_pull_for_start, vars_to_pull_for_end = self.consolidate_pull_operations(run_regularly_operations)
        engine_tmp = GeNNCodeObject.templater.engine(None, None,
                                                     neuron_models=self.neuron_models,
                                                     spikegenerator_models=self.spikegenerator_models,
                                                     synapse_models=self.synapse_models,
                                                     spike_monitor_models=self.spike_monitor_models,
                                                     rate_monitor_models=self.rate_monitor_models,
                                                     state_monitor_models=self.state_monitor_models,
                                                     run_regularly_operations=run_regularly_operations,
                                                     maximum_run_time=maximum_run_time,
                                                     run_reg_state_monitor_operations=run_reg_state_monitor_operations,
                                                     vars_to_pull_for_start=vars_to_pull_for_start,
                                                     vars_to_pull_for_end=vars_to_pull_for_end,
                                                     groupDict=self.groupDict
                                                     )
        writer.write('engine.*', engine_tmp)

    def generate_makefile(self, directory, use_GPU):
        if os.sys.platform == 'win32':
            project_tmp = GeNNCodeObject.templater.project_vcxproj(None, None,
                                                                   source_files=self.source_files)
            with open(os.path.join(directory, 'project.vcxproj'), 'w') as f:
                f.write(project_tmp)
        else:
            compile_args_gcc = get_gcc_compile_args()
            linker_flags = ' '.join(prefs.codegen.cpp.extra_link_args)
            makefile_tmp = GeNNCodeObject.templater.Makefile(None, None,
                                                             source_files=self.source_files,
                                                             compiler_flags=compile_args_gcc,
                                                             linker_flags=linker_flags)
            with open(os.path.join(directory, 'Makefile'), 'w') as f:
                f.write(makefile_tmp)

    def generate_objects_source(self, arange_arrays, net, static_array_specs,
                                synapses, writer):
        # ------------------------------------------------------------------------------
        # create the objects.cpp and objects.h code
        the_objects = list(self.code_objects.values())
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
            networks=[],  # We don't want to create any networks
            get_array_filename=self.get_array_filename,
            get_array_name=self.get_array_name,
            code_objects=the_objects
        )
        writer.write('objects.*', arr_tmp)
        self.header_files.add('objects.h')
        self.source_files.add('objects.cpp')

    def copy_source_files(self, writer, directory):
        # Copies brianlib, spikequeue and randomkit
        super().copy_source_files(writer, directory)

        # Copy the b2glib directory
        b2glib_dir = os.path.join(
            os.path.split(inspect.getsourcefile(GeNNCodeObject))[0],
            'b2glib')
        b2glib_files = copy_directory(b2glib_dir,
                                      os.path.join(directory, 'b2glib'))
        for file in b2glib_files:
            if file.lower().endswith('.cpp'):
                self.source_files.add('b2glib/' + file)
            elif file.lower().endswith('.h'):
                self.header_files.add('b2glib/' + file)

    def network_run(self, net, duration, report=None, report_period=10 * second,
                    namespace=None, profile=None, level=0, **kwds):
        self.kernel_timings = profile
        # Allow setting `profile` in the `set_device` call (used e.g. in brian2cuda
        # SpeedTest configurations)
        if profile is None:
            self.kernel_timings = self.build_options.pop("profile", None)
            # If not set, check the deprecated preference
            if profile is None and prefs.devices.genn.kernel_timing:
                logger.warn("The preference 'devices.genn.kernel_timing' is "
                            "deprecated, please set profile=True instead")
                self.kernel_timings = True
        if kwds:
            logger.warn(('Unsupported keyword argument(s) provided for run: '
                         + '%s') % ', '.join(kwds.keys()))

        if self.run_duration is not None:
            raise NotImplementedError(
                'Only a single run statement is supported for the genn device.')
        self.run_duration = float(duration)
        for obj in net.objects:
            if (obj.clock.name != 'defaultclock') and (obj.__class__ not in (CodeRunner, StateMonitor)):
                raise NotImplementedError(
                    'Multiple clocks are not supported for the genn device')

        for obj in net.objects:
            if hasattr(obj, '_linked_variables'):
                if len(obj._linked_variables) > 0:
                    raise NotImplementedError(
                        'The genn device does not support linked variables')

        print('running brian code generation ...')

        self.net = net
        # We need to store all objects, since MagicNetwork.after_run will clear
        # Network.objects to avoid memory leaks
        self.net_objects = _get_all_objects(self.net.objects)
        super().network_run(net=net, duration=duration,
                            report=report,
                            report_period=report_period,
                            namespace=namespace,
                            level=level + 1,
                            profile=False)

        self.run_statement_used = True


    def network_get_profiling_info(self, net):
        fname = os.path.join(self.project_dir, 'test_output', 'test.time')
        if not self.kernel_timings:
            raise ValueError("No profiling info collected (need to set "
                             "profile = True ?)")
        net._profiling_info = []
        keys = ['neuronUpdateTime',
                'presynapticUpdateTime',
                'postsynapticUpdateTime',
                'synapseDynamicsTime',
                'initTime',
                'initSparseTime']
        with open(fname) as f:
            # times are appended as new line in each run
            last_line = f.read().splitlines()[-1]
        times = last_line.split()
        n_time = len(times)
        n_key = len(keys)
        assert n_time == n_key, (
            f'{n_time} != {n_key} \ntimes: {times}\nkeys: {keys}'
        )
        for key, time in zip(keys, times):
            net._profiling_info.append((key, float(time)*second))
        return sorted(net._profiling_info, key=lambda item: item[1],
                      reverse=True)


# ------------------------------------------------------------------------------
# End of GeNNDevice
# ------------------------------------------------------------------------------

genn_device = GeNNDevice()

all_devices['genn'] = genn_device
