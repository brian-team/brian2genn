'''
Preferences that relate to the brian2genn interface.
'''

from brian2.core.preferences import *

def valid_connectivity(value):
    for v in ['DENSE', 'SPARSE', 'AUTO']:
        if value == v:
            return True
    return False

def valid_connectivity_decision(expr):
    Npre= 10
    Npost= 10
    Nsyn= 50
    try:
        val= eval(expr)
    except Exception:
        return False
    if val == True or val == False:
        return True
    return False
    

prefs.register_preferences(
    'devices.genn',
    'Preferences that relate to the brian2genn interface',
    connectivity= BrianPreference(
        validator= valid_connectivity,
        docs='''
        This preference determines which connectivity scheme is to be employed within GeNN. The valid alternatives are 'DENSE', 'SPARSE', and 'AUTO'. For 'DENSE' the GeNN dense matrix methods are used for all connectivity matrices. When 'SPARSE' is chosen, the GeNN sparse matrix representations are used. For 'AUTO', GeNN decides on a per-synapse population basis whether to use dense or sparse representations based on the evaluation of a decision function that returns whether to use dense or sparse methods based on the number of pre-synaptic neurons, post-synaptic neurons and the number of existing connections. The default decision function chooses sparse methods whenever, the number of existing connections  is less than 25% of all possible connections. A custom decision expression can be provided with the preference 'connectivity_decision'.''',
        default= 'SPARSE'
    ),
    connectivity_decision= BrianPreference(
        validator= valid_connectivity_decision,
        docs= '''
        This preference allows users to set their own logical expression for the decision whether to use dense or sparse matrix methods based on Npre, Npost and Nsyn. Users should provide a valid Python expression that involves the variable sNpre (pre-synaptic neurons number), Npost (post-synaptic neuron number) and Nsyn (number of existing synapses) and return <True> for using dense matrices and <False> for using sparse. The default behaviour, e.g., corresponds to the logical expression 'Nsyn > 0.25*Npre*Npost'. ''',
        default= 'Nsyn > 0.25*Npre*Npost'
    ),
    unix_compiler_flags= BrianPreference(
        docs= '''
        This preference allows users to set their own compiler flags for the eventual compilation of GeNN generated code. The flags will be applied both for the nvcc compilation and C++ compiler compilation (e.g. gcc, clang). This preference is for unix-based operating systems. ''',
        default= '-O3 -ffast-math'
    ),
    windows_compiler_flags= BrianPreference(
        docs= '''
                This preference allows users to set their own compiler flags for the eventual compilation of GeNN generated code. The flags will be applied both for the nvcc compilation and C++ compiler compilation (e.g. MCVC cl). This preference is for the windows operating system. ''',
        default= '/O2'
    ),
    cpu_only= BrianPreference(
        docs= '''
        Set this preference to True if you want to compile in GeNN's "CPU only" mode. By default this flag is False and GeNN compiles both a GPU and a CPU version. Which one is run in that case is decided by the useGPU flag in the device.buld command invocation. You might want cpu_only mode if you want to use GeNN on a system that does not have CUDA installed or does not have hardware that supports CUDA.''',
        default= False
    )
)

    
  
        
