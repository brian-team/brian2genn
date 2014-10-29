import brian2
import os
import shutil
import sys
from StringIO import StringIO
from brian2.tests.features import (Configuration, DefaultConfiguration,
                                   run_feature_tests)

class GeNNConfiguration(Configuration):
    name = 'GeNN'
    def before_run(self):
        brian2.prefs.read_preference_file(StringIO(brian2.prefs.defaults_as_file))
        brian2.set_device('genn')
        
    def after_run(self):
        if os.path.exists('testing_dir'):
            shutil.rmtree('testing_dir')
        brian2.device.build(directory='testing_dir', compile=True, run=True,
                            use_GPU=True)

if __name__=='__main__':
    print run_feature_tests(configurations=[DefaultConfiguration, GeNNConfiguration])
    