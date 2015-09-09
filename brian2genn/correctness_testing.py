'''
Definitions of teh configuration for testing
'''
import brian2
import os
import shutil
import sys
import brian2genn
from brian2.tests.features import (Configuration, DefaultConfiguration,
                                   run_feature_tests, run_single_feature_test)

class GeNNConfiguration(Configuration):
    name = 'GeNN'
    def before_run(self):
#        brian2.prefs.reset_to_defaults()
        brian2.prefs.codegen.loop_invariant_optimisations = False
        brian2.set_device('genn')
        
    def after_run(self):
        if os.path.exists('GeNNworkspace'):
            shutil.rmtree('GeNNworkspace')
        brian2.device.build(directory='GeNNworkspace', compile=True, run=True,
                            use_GPU=True)

