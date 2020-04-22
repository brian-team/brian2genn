'''
Preferences that relate to the brian2genn interface.
'''
import os

from brian2.core.preferences import *


prefs.register_preferences(
    'devices.genn',
    'Preferences that relate to the brian2genn interface',
    connectivity=BrianPreference(
        validator=lambda value: value in ['DENSE', 'SPARSE'],
        docs='''
        This preference determines which connectivity scheme is to be employed within GeNN. The valid alternatives are 'DENSE' and 'SPARSE'. For 'DENSE' the GeNN dense matrix methods are used for all connectivity matrices. When 'SPARSE' is chosen, the GeNN sparse matrix representations are used.''',
        default='SPARSE'
    ),
    path=BrianPreference(
        docs='''The path to the GeNN installation (if not set, the version of GeNN in the path will be used instead)''',
        default=None,
        validator=lambda value: value is None or os.path.isdir(value)
    ),
    kernel_timing=BrianPreference(
        docs='''This preference determines whether GeNN should record kernel runtimes; note that this can affect performance.''',
        default=False,
    )
)

prefs.register_preferences(
    'devices.genn.cuda_backend',
    'Preferenes that relate to the CUDA backend for the brian2genn interface',
    cuda_path=BrianPreference(
        docs='''The path to the CUDA installation (if not set, the CUDA_PATH environment variable will be used instead)''',
        default=None,
        validator=lambda value: value is None or os.path.isdir(value)
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
    synapse_span_type=BrianPreference(
        docs='''This preference determines whether the spanType (parallelization mode) for a synapse population should be set to pre-synapstic or post-synaptic.''',
        default='POSTSYNAPTIC',
        validator=lambda value: value in ['PRESYNAPTIC', 'POSTSYNAPTIC'],
    )
)
