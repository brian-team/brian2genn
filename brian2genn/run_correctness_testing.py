import brian2genn
from brian2.tests.features import (Configuration, DefaultConfiguration,
                                   run_feature_tests, run_single_feature_test)
from brian2genn.correctness_testing import GeNNConfiguration

from brian2.tests.features.synapses import SynapsesPre, SynapsesPost
#c = GeNNConfiguration()
#c.before_run()
#f = SynapsesPre()
#f.run()
#c.after_run()
#run_single_feature_test(GeNNConfiguration, SynapsesPre).tables_and_exceptions
#print run_feature_tests(configurations=[DefaultConfiguration,
#                                        GeNNConfiguration],
#                        feature_tests=[SynapsesPre,
#                                       SynapsesPost]).tables_and_exceptions
# print run_feature_tests(configurations=[DefaultConfiguration,
#                                         GeNNConfiguration],
#                         feature_tests=[SynapsesPre]).tables_and_exceptions
print run_feature_tests(configurations=[DefaultConfiguration,
                                    GeNNConfiguration]).tables_and_exceptions
