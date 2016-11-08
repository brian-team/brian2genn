'''
Definitions of the configuration for correctness testing.
'''
import brian2
import os
import shutil
import sys
import brian2genn
from brian2.tests.features import (Configuration, DefaultConfiguration,
                                   run_feature_tests, run_single_feature_test)

__all__ = ['GeNNConfiguration',
           'GeNNConfigurationCPU',
           'GeNNConfigurationOptimized']

class GeNNConfiguration(Configuration):
    name = 'GeNN'
    def before_run(self):
        brian2.prefs.codegen.cpp.extra_compile_args = []
        brian2.prefs._backup()
        brian2.set_device('genn')

class GeNNConfigurationCPU(Configuration):
    name = 'GeNN_CPU'
    def before_run(self):
        brian2.prefs.codegen.cpp.extra_compile_args = []
        brian2.prefs._backup()
        brian2.set_device('genn', use_GPU=False)

class GeNNConfigurationOptimized(Configuration):
    name = 'GeNN_optimized'
    def before_run(self):
        brian2.prefs.reset_to_defaults()
        brian2.prefs._backup()
        brian2.set_device('genn')
