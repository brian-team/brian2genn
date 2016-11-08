import brian2genn
import brian2
from brian2.tests.features import (Configuration, DefaultConfiguration,
                                   run_feature_tests, run_single_feature_test)
from brian2genn.correctness_testing import GeNNConfiguration
from brian2.tests.features.synapses import *
from brian2.tests.features.neurongroup import *
from brian2.tests.features.monitors import *
from brian2.tests.features.speed import *
from brian2.tests.features.input import *
from brian2.tests.features import CPPStandaloneConfiguration
from brian2 import prefs

if __name__=='__main__':
    brian2.test([], test_codegen_independent=False, test_standalone='genn',
                fail_for_not_implemented=False)
