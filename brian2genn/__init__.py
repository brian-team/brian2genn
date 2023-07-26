import os
import warnings

from brian2genn.codeobject import GeNNCodeObject
from brian2genn.device import genn_device
# Register preferences and the binomial implementation:
import brian2genn.preferences
import brian2genn.binomial


try:
    from ._version import __version__, __version_tuple__
except ImportError:
    try:
        from setuptools_scm import get_version

        __version__ = get_version(
            root="..",
            relative_to=__file__,
            version_scheme="post-release",
            local_scheme="no-local-version",
        )
        __version_tuple__ = tuple(int(x) if x.isdigit() else x
                                  for x in __version__.split("."))
    except ImportError:
        warnings.warn(
            "Cannot determine Brian version, running from source and "
            "setuptools_scm is not installed."
        )
        __version__ = "unknown"
        __version_tuple__ = (0, 0, 0)


def example_run(debug=False, **build_options):
    '''
    Run a simple example simulation that test whether the Brian2/Brian2GeNN/GeNN
    pipeline is working correctly.

    Parameters
    ----------
    debug : bool
        Whether to display debug information (e.g. compilation output) during
        the run. Defaults to ``False``.
    build_options : dict
        Additional options that will be forwarded to the ``set_device`` call,
        e.g. ``use_GPU=False``.
    '''
    from brian2.devices.device import set_device, reset_device
    from brian2 import ms, NeuronGroup, run
    from brian2.utils.logger import std_silent
    import numpy as np
    from numpy.testing import assert_allclose
    from tempfile import mkdtemp
    import shutil
    with std_silent(debug):
        test_dir = mkdtemp(prefix='brian2genn_test')
        set_device('genn', directory=test_dir, debug=debug, **build_options)
        N = 100
        tau = 10*ms
        eqs = '''
        dV/dt = -V/tau: 1
        '''
        G = NeuronGroup(N, eqs, threshold='V>1', reset='V=0', refractory=5 * ms,
                        method='linear')
        G.V = 'i/100.'
        run(1*ms)
        assert_allclose(G.V, np.arange(100)/100.*np.exp(-1*ms/tau))
        shutil.rmtree(test_dir, ignore_errors=True)
        reset_device()
    print('Example run was successful.')
