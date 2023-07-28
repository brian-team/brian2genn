'''
Preferences that relate to the brian2genn interface.
'''
import os

from brian2.core.preferences import *

class DeprecatedValidator:
    '''
    'Validator' for deprecated preferences
    
    Used as a validator for preferences that have been (rudely) deprecated
    '''
    def __init__(self, message):
        self.message = message

    def __call__(self, value):
        if value is not None:
            raise PreferenceError(self.message)
        return True

prefs.register_preferences(
    'devices.genn',
    'Preferences that relate to the brian2genn interface',
    connectivity=BrianPreference(
        validator=lambda value: value in ['DENSE', 'SPARSE'],
        docs='''
        This preference determines which connectivity scheme is to be employed within GeNN. The valid alternatives are 'DENSE' and 'SPARSE'. For 'DENSE' the GeNN dense matrix methods are used for all connectivity matrices. When 'SPARSE' is chosen, the GeNN sparse matrix representations are used.''',
        default='SPARSE'
    ),
    extra_compile_args_nvcc=BrianPreference(
        docs='''Extra compile arguments (a list of strings) to pass to the nvcc compiler.''',
        default=None,
        validator=DeprecatedValidator('This preference is no longer supported by GeNN 4, please set devices.gennn.cuda_backend.extra_compile_args_nvcc instead.')
    ),
    auto_choose_device=BrianPreference(
        validator=DeprecatedValidator('This preference is no longer supported by GeNN 4, please use the devices.genn.cuda_backend.device_select preference instead.'),
        docs='''The GeNN preference autoChooseDevice that determines whether or not a GPU should be chosen automatically when multiple CUDA enabled devices are present.''',
        default=None,
    ),
    default_device=BrianPreference(
        validator=DeprecatedValidator('This preference is no longer supported by GeNN 4, please set devices.genn.cuda_backend.device_select=\'MANUAL\' and use the devices.genn.cuda_backend.manual_device preference instead.'),
        docs='''The GeNN preference defaultDevice that determines CUDA enabled device should be used if it is not automatically chosen.''',
        default=None,
    ),
    optimise_blocksize=BrianPreference(
        validator=DeprecatedValidator('This preference is no longer supported by GeNN 4, please use the devices.genn.cuda_backend.blocksize_select_method preference instead.'),
        docs='''The GeNN preference optimiseBlockSize that determines whether GeNN should use its internal algorithms to optimise the different block sizes.''',
        default=None,
    ),
    pre_synapse_reset_blocksize=BrianPreference(
        validator=DeprecatedValidator('This preference is no longer supported by GeNN 4, please set devices.genn.cuda_backend.blocksize_select_method=\'MANUAL\' and use the devices.genn.cuda_backend.pre_synapse_reset_blocksize preference instead.'),
        docs='''The GeNN preference preSynapseResetBlockSize that determines the CUDA block size for the pre-synapse reset kernel if not set automatically by GeNN's block size optimisation.''',
        default=None,
    ),
    neuron_blocksize=BrianPreference(
        validator=DeprecatedValidator('This preference is no longer supported by GeNN 4, please set devices.genn.cuda_backend.blocksize_select_method=\'MANUAL\' and use the devices.genn.cuda_backend.neuron_blocksize preference instead.'),
        docs='''The GeNN preference neuronBlockSize that determines the CUDA block size for the neuron kernel if not set automatically by GeNN's block size optimisation.''',
        default=None,
    ),
    synapse_blocksize=BrianPreference(
        validator=DeprecatedValidator('This preference is no longer supported by GeNN 4, please set devices.genn.cuda_backend.blocksize_select_method=\'MANUAL\' and use the devices.genn.cuda_backend.synapse_blocksize preference instead.'),
        docs='''The GeNN preference synapseBlockSize that determines the CUDA block size for the neuron kernel if not set automatically by GeNN's block size optimisation.''',
        default=None,
    ),
    learning_blocksize=BrianPreference(
        validator=DeprecatedValidator('This preference is no longer supported by GeNN 4, please set devices.genn.cuda_backend.blocksize_select_method=\'MANUAL\' and use the devices.genn.cuda_backend.learning_blocksize preference instead.'),
        docs='''The GeNN preference learningBlockSize that determines the CUDA block size for the neuron kernel if not set automatically by GeNN's block size optimisation.''',
        default=None,
    ),
    synapse_dynamics_blocksize=BrianPreference(
        validator=DeprecatedValidator('This preference is no longer supported by GeNN 4, please set devices.genn.cuda_backend.blocksize_select_method=\'MANUAL\' and use the devices.genn.cuda_backend.synapse_dynamics_blocksize preference instead.'),
        docs='''The GeNN preference synapseDynamicsBlockSize that determines the CUDA block size for the neuron kernel if not set automatically by GeNN's block size optimisation.''',
        default=None,
    ),
    init_blocksize=BrianPreference(
        validator=DeprecatedValidator('This preference is no longer supported by GeNN 4, please set devices.genn.cuda_backend.blocksize_select_method=\'MANUAL\' and use the devices.genn.cuda_backend.init_blocksize preference instead.'),
        docs='''The GeNN preference initBlockSize that determines the CUDA block size for the neuron kernel if not set automatically by GeNN's block size optimisation.''',
        default=None,
    ),
    init_sparse_blocksize=BrianPreference(
        validator=DeprecatedValidator('This preference is no longer supported by GeNN 4, please set devices.genn.cuda_backend.blocksize_select_method=\'MANUAL\' and use the devices.genn.cuda_backend.init_sparse_blocksize preference instead.'),
        docs='''The GeNN preference initSparseBlockSize that determines the CUDA block size for the neuron kernel if not set automatically by GeNN's block size optimisation.''',
        default=None,
    ),
    synapse_span_type=BrianPreference(
        docs='''This preference determines whether the spanType (parallelization mode) for a synapse population should be set to pre-synapstic or post-synaptic.''',
        default='POSTSYNAPTIC',
        validator=lambda value: value in ['PRESYNAPTIC', 'POSTSYNAPTIC'],
    ),
    path=BrianPreference(
        docs='''The path to the GeNN installation (if not set, the version of GeNN in the path will be used instead)''',
        default=None,
        validator=lambda value: value is None or os.path.isdir(value)
    ),
    kernel_timing=BrianPreference(
        docs='''This preference determines whether GeNN should record kernel runtimes; note that this can affect performance.
        This preference is deprecated, use profile=True in the set_device or run call instead.''',
        default=False,
    )
)

prefs.register_preferences(
    'devices.genn.cuda_backend',
    'Preferences that relate to the CUDA backend for the brian2genn interface',
    cuda_path=BrianPreference(
        docs='''The path to the CUDA installation (if not set, the CUDA_PATH environment variable will be used instead)''',
        default=None,
        validator=lambda value: value is None or os.path.isdir(value)
    ),
    extra_compile_args_nvcc=BrianPreference(
        docs='''Extra compile arguments (a list of strings) to pass to the nvcc compiler.''',
        default=[]
    ),
    device_select=BrianPreference(
        validator=lambda value: value in ['OPTIMAL', 'MOST_MEMORY', 'MANUAL'],
        docs='''The GeNN preference deviceSelectMethod that determines how to chose which GPU device to use.''',
        default='OPTIMAL',
    ),
    manual_device=BrianPreference(
        docs='''The GeNN preference manualDeviceID that determines CUDA enabled device should be used if device_select is set to MANUAL.''',
        default=0,
    ),
    blocksize_select_method=BrianPreference(
        validator=lambda value: value in ['OCCUPANCY', 'MANUAL'],
        docs='''The GeNN preference blockSizeSelectMethod that determines whether GeNN should use its internal algorithms to optimise the different block sizes.''',
        default='OCCUPANCY',
    ),
    pre_neuron_reset_blocksize=BrianPreference(
        docs='''The GeNN preference preNeuronResetBlockSize that determines the CUDA block size for the pre-neuron reset kernel if blocksize_select_method is set to MANUAL.''',
        default=32,
    ),
    pre_synapse_reset_blocksize=BrianPreference(
        docs='''The GeNN preference preSynapseResetBlockSize that determines the CUDA block size for the pre-synapse reset kernel if blocksize_select_method is set to MANUAL.''',
        default=32,
    ),
    neuron_blocksize=BrianPreference(
        docs='''The GeNN preference neuronBlockSize that determines the CUDA block size for the neuron kernel if blocksize_select_method is set to MANUAL.''',
        default=32,
    ),
    synapse_blocksize=BrianPreference(
        docs='''The GeNN preference synapseBlockSize that determines the CUDA block size for the neuron kernel if blocksize_select_method is set to MANUAL.''',
        default=32,
    ),
    learning_blocksize=BrianPreference(
        docs='''The GeNN preference learningBlockSize that determines the CUDA block size for the neuron kernel if blocksize_select_method is set to MANUAL.''',
        default=32,
    ),
    synapse_dynamics_blocksize=BrianPreference(
        docs='''The GeNN preference synapseDynamicsBlockSize that determines the CUDA block size for the neuron kernel if blocksize_select_method is set to MANUAL.''',
        default=32,
    ),
    init_blocksize=BrianPreference(
        docs='''The GeNN preference initBlockSize that determines the CUDA block size for the neuron kernel if blocksize_select_method is set to MANUAL.''',
        default=32,
    ),
    init_sparse_blocksize=BrianPreference(
        docs='''The GeNN preference initSparseBlockSize that determines the CUDA block size for the neuron kernel if blocksize_select_method is set to MANUAL.''',
        default=32,
    ),
)
