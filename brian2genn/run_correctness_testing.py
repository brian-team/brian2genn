import brian2genn
from brian2.tests.features import (Configuration, DefaultConfiguration,
                                   run_feature_tests, run_single_feature_test)
from brian2genn.correctness_testing import GeNNConfiguration

from brian2.tests.features.synapses import SynapsesPre
#c = GeNNConfiguration()
#c.before_run()
#f = SynapsesPre()
#f.run()
#c.after_run()
#run_single_feature_test(GeNNConfiguration, SynapsesPre)
print run_feature_tests(configurations=[DefaultConfiguration, GeNNConfiguration])
