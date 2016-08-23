'''
Implementation of `BinomialFunction`
'''
import numpy as np

from brian2.core.base import Nameable
from brian2.core.functions import Function, DEFAULT_FUNCTIONS
from brian2.units.fundamentalunits import check_units
from brian2.utils.stringtools import replace
from brian2.input.binomial import _pre_calc_constants_approximated, _pre_calc_constants, BinomialFunction


def _generate_genn_code(n, p, use_normal, name):
    # GeNN implementation
    # Inversion transform sampling
    if use_normal:
        loc, scale = _pre_calc_constants_approximated(n, p)
        loc = n*p
        scale = np.sqrt(n*p*(1-p))
        genn_code = '''
        #ifdef CPU_ONLY
        float %NAME%(uint64_t seed)
        #else
        __host__ __device__ float %NAME%(uint64_t seed)
        #endif
        {
            return _randn(seed) * %SCALE% + %LOC%;
        }
        '''
        genn_code = replace(genn_code, {'%SCALE%': '%.15f' % scale,
                                      '%LOC%': '%.15f' % loc,
                                      '%NAME%': name})
        dependencies = {'_randn': DEFAULT_FUNCTIONS['randn']}
    else:
        reverse, q, P, qn, bound = _pre_calc_constants(n, p)
        # The following code is an almost exact copy of numpy's
        # rk_binomial_inversion function
        # (numpy/random/mtrand/distributions.c)
        genn_code = '''
        #ifdef CPU_ONLY
        long %NAME%(uint64_t seed)
        #else
        __host__ __device__ long %NAME%(uint64_t seed)
        #endif
        {
            long X = 0;
            double px = %QN%;
            double U = _rand(seed);
            while (U > px)
            {
                X++;
                if (X > %BOUND%)
                {
                    X = 0;
                    px = %QN%;
                    U = _rand(seed);
                } else
                {
                    U -= px;
                    px = ((%N%-X+1) * %P% * px)/(X*%Q%);
                }
            }
            return %RETURN_VALUE%;
        }
        '''
        genn_code = replace(genn_code, {'%N%': '%d' % n,
                                      '%P%': '%.15f' % P,
                                      '%Q%': '%.15f' % q,
                                      '%QN%': '%.15f' % qn,
                                      '%BOUND%': '%.15f' % bound,
                                      '%RETURN_VALUE%': '%d-X' % n if reverse else 'X',
                                      '%NAME%': name})
        dependencies = {'_rand': DEFAULT_FUNCTIONS['rand']}

    return {'support_code': genn_code}, dependencies


BinomialFunction.implementations.update({'genn': _generate_genn_code})
