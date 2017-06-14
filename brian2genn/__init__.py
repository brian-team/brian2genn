import os
import warnings

from .codeobject import GeNNCodeObject
from .device import genn_device
import binomial
import preferences

from pkg_resources import get_distribution, DistributionNotFound
try:
    __version__ = get_distribution(__name__).version
except DistributionNotFound:
    # Apparently we are running directly from a git clone, let
    # setuptools_scm fetch the version from git
    try:
        from setuptools_scm import get_version
        __version__ = get_version(relative_to=os.path.dirname(__file__))
    except ImportError:
        warnings.warn('Cannot determine brian2genn version (running directly '
                      'from source code and no setuptools_scm package '
                      'available).')
