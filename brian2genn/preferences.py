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
    extra_compile_args_nvcc=BrianPreference(
        docs='''Extra compile arguments (a list of strings) to pass to the nvcc compiler.''',
        default=['-O3']
    ),
    path=BrianPreference(
        docs='''The path to the GeNN installation (if not set, the GENN_PATH environment variable will be used instead)''',
        default=None,
        validator=lambda value: value is None or os.path.isdir(value)
    ),
    cuda_path=BrianPreference(
        docs='''The path to the CUDA installation (if not set, the CUDA_PATH environment variable will be used instead)''',
        default=None,
        validator=lambda value: value is None or os.path.isdir(value)
    ),
    auto_choose_device=BrianPreference(
        docs='''The GeNN preference autoChooseDevice that determines whether or not a GPU should be chosen automatically when multiple CUDA enabled devices are present.''',
        default=True,
    ),
    default_device=BrianPreference(
        docs='''The GeNN preference defaultDevice that determines CUDA enabled device should be used if it is not automatically chosen.''',
        default=0,
    ),
    optimise_blocksize=BrianPreference(
        docs='''The GeNN preference optimiseBlockSize that determines whether GeNN should use its internal algorithms to optimise the different block sizes.''',
        default=True,
    ),
    pre_synapse_reset_blocksize=BrianPreference(
        docs='''The GeNN preference preSynapseResetBlockSize that determines the CUDA block size for the pre-synapse reset kernel if not set automatically by GeNN's block size optimisation.''',
        default=32,
    ),
    neuron_blocksize=BrianPreference(
        docs='''The GeNN preference neuronBlockSize that determines the CUDA block size for the neuron kernel if not set automatically by GeNN's block size optimisation.''',
        default=32,
    ),
    synapse_blocksize=BrianPreference(
        docs='''The GeNN preference synapseBlockSize that determines the CUDA block size for the neuron kernel if not set automatically by GeNN's block size optimisation.''',
        default=32,
    ),
    learning_blocksize=BrianPreference(
        docs='''The GeNN preference learningBlockSize that determines the CUDA block size for the neuron kernel if not set automatically by GeNN's block size optimisation.''',
        default=32,
    ),
    synapse_dynamics_blocksize=BrianPreference(
        docs='''The GeNN preference synapseDynamicsBlockSize that determines the CUDA block size for the neuron kernel if not set automatically by GeNN's block size optimisation.''',
        default=32,
    ),
    init_blocksize=BrianPreference(
        docs='''The GeNN preference initBlockSize that determines the CUDA block size for the neuron kernel if not set automatically by GeNN's block size optimisation.''',
        default=32,
    ),
    init_sparse_blocksize=BrianPreference(
        docs='''The GeNN preference initSparseBlockSize that determines the CUDA block size for the neuron kernel if not set automatically by GeNN's block size optimisation.''',
        default=32,
    ),
    synapse_span_type=BrianPreference(
        docs='''This preference determines whether the spanType (parallelization mode) for a synapse population should be set to pre-synapstic or post-synaptic.''',
        default='POSTSYNAPTIC',
        validator=lambda value: value in ['PRESYNAPTIC', 'POSTSYNAPTIC'],
    ),
    kernel_timing=BrianPreference(
        docs='''This preference determines whether GeNN should record kernel runtimes; note that this can affect performance.''',
        default=False,
    )
)
