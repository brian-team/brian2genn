'''
TODO: use preferences to get arguments to Language
'''
import numpy

from brian2.utils.stringtools import (deindent, stripped_deindented_lines,
                                      word_substitute)
from brian2.utils.logger import get_logger
from brian2.core.functions import (Function, FunctionImplementation,
                                   DEFAULT_FUNCTIONS)
from brian2.core.preferences import brian_prefs, BrianPreference
from brian2.core.variables import ArrayVariable

from brian2.codegen.generators.base import CodeGenerator
from brian2.codegen.generators.cpp_generator import CPPCodeGenerator, c_data_type

from .renderer import GeNNNodeRenderer

logger = get_logger(__name__)

__all__ = ['GeNNCodeGenerator',
           'c_data_type',
           ]


# Preferences
brian_prefs.register_preferences(
    'codegen.generators.genn',
    'GeNN codegen preferences',
    restrict_keyword = BrianPreference(
        default='__restrict__',
        docs='''
        The keyword used for the given compiler to declare pointers as restricted.
        
        This keyword is different on different compilers, the default is for gcc.
        ''',
        ),
    flush_denormals = BrianPreference(
        default=False,
        docs='''
        Adds code to flush denormals to zero.
        
        The code is gcc and architecture specific, so may not compile on all
        platforms. The code, for reference is::

            #define CSR_FLUSH_TO_ZERO         (1 << 15)
            unsigned csr = __builtin_ia32_stmxcsr();
            csr |= CSR_FLUSH_TO_ZERO;
            __builtin_ia32_ldmxcsr(csr);
            
        Found at `<http://stackoverflow.com/questions/2487653/avoiding-denormal-values-in-c>`_.
        ''',
        ),
    )


class GeNNCodeGenerator(CPPCodeGenerator):
    '''
    GeNN interface language
    
    GeNN code templates should provide Jinja2 macros with the following names:
    
    ``model``
        The main loop.
    ``support_code``
        The support code (function definitions, etc.), compiled in a separate
        file.
        
    For user-defined functions, there are two keys to provide:
    
    ``support_code``
        The function definition which will be added to the support code.
    ``hashdefine_code``
        The ``#define`` code added to the main loop.
        
    '''

    class_name = 'genn'

    def __init__(self, c_data_type=c_data_type):
        super(GeNNCodeGenerator, self).__init__(*args, **kwds)
        self.restrict = brian_prefs['codegen.generators.genn.restrict_keyword'] + ' '
        self.flush_denormals = brian_prefs['codegen.generators.genn.flush_denormals']
        self.c_data_type = c_data_type

    def translate_expression(self, expr):
        for varname, var in self.variables.iteritems():
            if isinstance(var, Function):
                impl_name = var.implementations[self.codeobj_class].name
                if impl_name is not None:
                    expr = word_substitute(expr, {varname: impl_name})
        return GeNNNodeRenderer().render_expr(expr).strip()

# No need to implement functions, they're just the same as C++
