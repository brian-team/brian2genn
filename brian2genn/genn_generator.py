'''
The code generator for the "genn" language. This is mostly C++ with some specific
decorators (mainly "__host__ __device__") to allow operation in a CUDA context.
'''

from brian2.utils.stringtools import (deindent, stripped_deindented_lines,
                                      word_substitute)
from brian2.utils.logger import get_logger
from brian2.parsing.rendering import CPPNodeRenderer
from brian2.core.functions import Function, DEFAULT_FUNCTIONS
from brian2.core.preferences import prefs
from brian2.core.variables import ArrayVariable
from brian2.codegen.generators.base import CodeGenerator
from brian2.codegen.generators.cpp_generator import c_data_type
from brian2genn.insyn import check_pre_code

logger = get_logger('brian2.devices.genn')

__all__ = ['GeNNCodeGenerator']


def get_var_ndim(v, default_value=None):
    '''
    Helper function to get the ``ndim`` attribute of a `DynamicArrayVariable`,
    falling back to the previous name ``dimensions`` if necessary.

    Parameters
    ----------
    v : `ArrayVariable`
        The variable for which to retrieve the number of dimensions.
    default_value : optional
        A default value if the attribute does not exist

    Returns
    -------
    ndim : int
        Number of dimensions
    '''
    try:
        return v.ndim
    except AttributeError:
        try:
            return v.dimensions
        except AttributeError as ex:
            if default_value is not None:
                return default_value
            else:
                raise ex



def _mod_support_code():
    code = ''
    typestrs = ['int', 'float', 'double']
    floattypestrs = ['float', 'double']
    for ix, xtype in enumerate(typestrs):
        for iy, ytype in enumerate(typestrs):
            hightype = typestrs[max(ix, iy)]
            if xtype in floattypestrs or ytype in floattypestrs:
                expr = 'fmod(fmod(x, y)+y, y)'
            else:
                expr = '((x%y)+y)%y'
            code += '''
            #ifdef CPU_ONLY
            inline {hightype} _brian_mod({xtype} ux, {ytype} uy)
            #else
            __host__ __device__ inline {hightype} _brian_mod({xtype} ux, {ytype} uy)
            #endif
            {{
                const {hightype} x = ({hightype})ux;
                const {hightype} y = ({hightype})uy;
                return {expr};
            }}
            '''.format(hightype=hightype, xtype=xtype, ytype=ytype, expr=expr)
    return deindent(code)


class GeNNCodeGenerator(CodeGenerator):
    '''
    "GeNN language"
    
    For user-defined functions, there are two keys to provide:
    
    ``support_code``
        The function definition which will be added to the support code.
    ``hashdefine_code``
        The ``#define`` code added to the main loop.
    '''

    class_name = 'genn'

    universal_support_code = _mod_support_code() + deindent('''
    #ifdef _MSC_VER
    #define _brian_pow(x, y) (pow((double)(x), (y)))
    #else
    #define _brian_pow(x, y) (pow((x), (y)))
    #endif
    ''')

    def __init__(self, *args, **kwds):
        super(GeNNCodeGenerator, self).__init__(*args, **kwds)
        self.c_data_type = c_data_type

    @property
    def restrict(self):
        return prefs['codegen.generators.cpp.restrict_keyword'] + ' '

    @property
    def flush_denormals(self):
        return prefs['codegen.generators.cpp.flush_denormals']

    @staticmethod
    def get_array_name(var, access_data=True):
        # We have to do the import here to avoid circular import dependencies.
        from brian2.devices.device import get_device
        device = get_device()
        if access_data:
            return '_ptr' + device.get_array_name(var)
        else:
            return device.get_array_name(var, access_data=False)

    def translate_expression(self, expr):
        for varname, var in self.variables.iteritems():
            if isinstance(var, Function):
                impl_name = var.implementations[self.codeobj_class].name
                if impl_name is not None:
                    expr = word_substitute(expr, {varname: impl_name})
        return CPPNodeRenderer().render_expr(expr).strip()

    def translate_statement(self, statement):
        var, op, expr, comment = (statement.var, statement.op,
                                  statement.expr, statement.comment)
        if op == ':=':
            decl = self.c_data_type(statement.dtype) + ' '
            op = '='
        else:
            decl = ''
        code = decl + var + ' ' + op + ' ' + self.translate_expression(expr) + ';'
        if len(comment):
            code += ' // ' + comment
        return code
    
    def translate_to_read_arrays(self, statements):
        return []

    def translate_to_declarations(self, statements):
        return []

    def translate_to_statements(self, statements):
        read, write, indices, conditional_write_vars = self.arrays_helper(statements)
        lines = []
        # the actual code
        for stmt in statements:
            line = self.translate_statement(stmt)
            if stmt.var in conditional_write_vars:
                subs = {}
                condvar = conditional_write_vars[stmt.var]
                lines.append('if(%s)' % condvar)
                lines.append('    '+line)
            else:
                lines.append(line)
        return lines

    def translate_to_write_arrays(self, statements):
        return []

    def translate_one_statement_sequence(self, statements, scalar=False):
        if len(statements) and self.template_name=='synapses':
            _, _, _, conditional_write_vars = self.arrays_helper(statements)
            vars_pre = [k for k, v in self.variable_indices.items() if v=='_presynaptic_idx']
            vars_syn = [k for k, v in self.variable_indices.items() if v=='_idx']
            vars_post = [k for k, v in self.variable_indices.items() if v=='_postsynaptic_idx']
            if '_pre_codeobject' in self.name:
                post_write_var, statements = check_pre_code(self, statements,
                                                vars_pre, vars_syn, vars_post,
                                                conditional_write_vars)
                self.owner._genn_post_write_var = post_write_var
        lines = []
        lines += self.translate_to_statements(statements)
        code = '\n'.join(lines)
        return stripped_deindented_lines(code)

    def denormals_to_zero_code(self):
        if self.flush_denormals:
            return '''
            #define CSR_FLUSH_TO_ZERO         (1 << 15)
            unsigned csr = __builtin_ia32_stmxcsr();
            csr |= CSR_FLUSH_TO_ZERO;
            __builtin_ia32_ldmxcsr(csr);
            '''
        else:
            return ''

    def _add_user_function(self, varname, variable):
        impl = variable.implementations[self.codeobj_class]
        support_code = []
        hash_defines = []
        pointers = []
        user_functions = [(varname, variable)]
        funccode = impl.get_code(self.owner)
        if isinstance(funccode, basestring):
            funccode = {'support_code': funccode}
        if funccode is not None:
            # To make namespace variables available to functions, we
            # create global variables and assign to them in the main
            # code
            func_namespace = impl.get_namespace(self.owner) or {}
            for ns_key, ns_value in func_namespace.iteritems():
                if hasattr(ns_value, 'dtype'):
                    if ns_value.shape == ():
                        raise NotImplementedError((
                        'Directly replace scalar values in the function '
                        'instead of providing them via the namespace'))
                    type_str = c_data_type(ns_value.dtype) + '*'
                else:  # e.g. a function
                    type_str = 'py::object'
                support_code.append('static {0} _namespace{1};'.format(type_str,
                                                                       ns_key))
                pointers.append('_namespace{0} = {1};'.format(ns_key, ns_key))
            support_code.append(deindent(funccode.get('support_code', '')))
            hash_defines.append(deindent(funccode.get('hashdefine_code', '')))

        dep_hash_defines = []
        dep_pointers = []
        dep_support_code = []
        if impl.dependencies is not None:
            for dep_name, dep in impl.dependencies.iteritems():
                if dep_name not in self.variables:  # do not add a dependency twice
                    self.variables[dep_name] = dep
                    hd, ps, sc, uf = self._add_user_function(dep_name, dep)
                    dep_hash_defines.extend(hd)
                    dep_pointers.extend(ps)
                    dep_support_code.extend(sc)
                    user_functions.extend(uf)

        return (dep_hash_defines + hash_defines,
                dep_pointers + pointers,
                dep_support_code + support_code,
                user_functions)

    def determine_keywords(self):
        # set up the restricted pointers, these are used so that the compiler
        # knows there is no aliasing in the pointers, for optimisation
        pointers = []
        # It is possible that several different variable names refer to the
        # same array. E.g. in gapjunction code, v_pre and v_post refer to the
        # same array if a group is connected to itself
        handled_pointers = set()
        template_kwds = {}
        # Again, do the import here to avoid a circular dependency.
        from brian2.devices.device import get_device
        device = get_device()
        for varname, var in self.variables.iteritems():
            if isinstance(var, ArrayVariable):
                # This is the "true" array name, not the restricted pointer.
                array_name = device.get_array_name(var)
                pointer_name = self.get_array_name(var)
                if pointer_name in handled_pointers:
                    continue
                if get_var_ndim(var, 1) > 1:
                    continue  # multidimensional (dynamic) arrays have to be treated differently
                line = '{0}* {1} {2} = {3};'.format(self.c_data_type(var.dtype),
                                                    self.restrict,
                                                    pointer_name,
                                                    array_name)
                pointers.append(line)
                handled_pointers.add(pointer_name)

        # set up the functions
        user_functions = []
        support_code = []
        hash_defines = []
        for varname, variable in self.variables.items():
            if isinstance(variable, Function):
                hd, ps, sc, uf = self._add_user_function(varname, variable)
                user_functions.extend(uf)
                support_code.extend(sc)
                pointers.extend(ps)
                hash_defines.extend(hd)


        # delete the user-defined functions from the namespace and add the
        # function namespaces (if any)
        for funcname, func in user_functions:
            del self.variables[funcname]
            func_namespace = func.implementations[self.codeobj_class].get_namespace(self.owner)
            if func_namespace is not None:
                self.variables.update(func_namespace)

        support_code.append(self.universal_support_code)

        keywords = {'pointers_lines': stripped_deindented_lines('\n'.join(pointers)),
                    'support_code_lines': stripped_deindented_lines('\n'.join(support_code)),
                    'hashdefine_lines': stripped_deindented_lines('\n'.join(hash_defines)),
                    'denormals_code_lines': stripped_deindented_lines('\n'.join(self.denormals_to_zero_code())),
                    }
        keywords.update(template_kwds)
        return keywords

################################################################################
# Implement functions
################################################################################

# Functions that exist under the same name in C++
for func in ['sin', 'cos', 'tan', 'sinh', 'cosh', 'tanh', 'exp', 'log',
             'log10', 'sqrt', 'ceil', 'floor']:
    DEFAULT_FUNCTIONS[func].implementations.add_implementation(GeNNCodeGenerator,
                                                               code=None)

# Functions that need a name translation
for func, func_genn in [('arcsin', 'asin'), ('arccos', 'acos'), ('arctan', 'atan')]:
    DEFAULT_FUNCTIONS[func].implementations.add_implementation(GeNNCodeGenerator,
                                                               code=None,
                                                               name=func_genn)


abs_code = '''
#define _brian_abs std::abs
'''
DEFAULT_FUNCTIONS['abs'].implementations.add_implementation(GeNNCodeGenerator,
                                                            code=abs_code,
                                                            name='_brian_abs')


# Functions that need to be implemented specifically
randn_code = '''
#ifdef CPU_ONLY
inline double _ranf(uint64_t &seed)
#else
__host__ __device__ inline double _ranf(uint64_t &seed)
#endif
{
    uint64_t x;
    MYRAND(seed,x);
    return ((double)x)/MYRAND_MAX;
}

#ifdef CPU_ONLY
double _randn(uint64_t &seed)
#else
__host__ __device__ double _randn(uint64_t &seed)
#endif
{
     double x1, x2, w;
     double y1, y2;
     do {
         x1 = 2.0 * _ranf(seed) - 1.0;
         x2 = 2.0 * _ranf(seed) - 1.0;
         w = x1 * x1 + x2 * x2;
     } while ( w >= 1.0 );

     w = sqrt( (-2.0 * log( w ) ) / w );
     y1 = x1 * w;
     return y1;
}
'''

DEFAULT_FUNCTIONS['randn'].implementations.add_implementation(GeNNCodeGenerator,
                                                              code=randn_code,
                                                              name='_randn')

rand_code = '''
#ifdef CPU_ONLY
double _rand(uint64_t &seed)
#else
__host__ __device__ double _rand(uint64_t &seed)
#endif
{
        uint64_t x;
        MYRAND(seed,x);
    return ((double)x)/MYRAND_MAX;
}
'''
DEFAULT_FUNCTIONS['rand'].implementations.add_implementation(GeNNCodeGenerator,
                                                             code=rand_code,
                                                             name='_rand')

clip_code = '''
#ifdef CPU_ONLY
double _clip(const float value, const float a_min, const float a_max)
#else
__host__ __device__ double _clip(const float value, const float a_min, const float a_max)
#endif
{
    if (value < a_min)
        return a_min;
    if (value > a_max)
        return a_max;
    return value;
}
'''
DEFAULT_FUNCTIONS['clip'].implementations.add_implementation(GeNNCodeGenerator,
                                                             code=clip_code,
                                                             name='_clip')

int_code = '''
#ifdef CPU_ONLY
inline int int_(const bool value)
#else
__host__ __device__ inline int int_(const bool value)
#endif
{
    return value ? 1 : 0;
}
'''
DEFAULT_FUNCTIONS['int'].implementations.add_implementation(GeNNCodeGenerator,
                                                            code=int_code,
                                                            name='int_')

sign_code = '''
#ifdef CPU_ONLY
template <typename T> int sign_(T val)
#else
template <typename T> __host__ __device__ int sign_(T val)
#endif
{
    return (T(0) < val) - (val < T(0));
}
'''
DEFAULT_FUNCTIONS['sign'].implementations.add_implementation(GeNNCodeGenerator,
                                                             code=sign_code,
                                                             name='sign_')
