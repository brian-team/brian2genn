'''
Preferences that relate to the brian2genn interface.
'''

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
    unix_compiler_flags= BrianPreference(
        docs='''
        This preference allows users to set their own compiler flags for the eventual compilation of GeNN generated code. The flags will be applied both for the nvcc compilation and C++ compiler compilation (e.g. gcc, clang). This preference is for unix-based operating systems. ''',
        default='-O3 -ffast-math'
    ),
    windows_compiler_flags= BrianPreference(
        docs='''
                This preference allows users to set their own compiler flags for the eventual compilation of GeNN generated code. The flags will be applied both for the nvcc compilation and C++ compiler compilation (e.g. MCVC cl). This preference is for the windows operating system. ''',
        default='/O2'
    )
)
