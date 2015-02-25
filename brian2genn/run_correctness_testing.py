import brian2genn
from brian2.tests.features import (Configuration, DefaultConfiguration,
                                   run_feature_tests, run_single_feature_test)
from brian2genn.correctness_testing import GeNNConfiguration

from brian2.tests.features.synapses import SynapsesPre, SynapsesPost
from brian2.tests.features.neurongroup import NeuronGroupIntegrationLinear, NeuronGroupIntegrationEuler, NeuronGroupLIF
from brian2 import prefs

prefs.codegen.loop_invariant_optimisations = False

#c = GeNNConfiguration()
#c.before_run()
#f = SynapsesPre()
#f.run()
#c.after_run()
#print run_single_feature_test(GeNNConfiguration, NeuronGroupIntegrationLinear)
#print run_single_feature_test(DefaultConfiguration, SynapsesPost)
#.tables_and_exceptions
#print run_feature_tests(configurations=[DefaultConfiguration,
#                                        GeNNConfiguration],
#                        feature_tests=[SynapsesPre,
#                                       SynapsesPost]).tables_and_exceptions
#print run_feature_tests(configurations=[DefaultConfiguration, 
#                                         GeNNConfiguration],
#                         feature_tests=[NeuronGroupIntegrationLinear]).tables_and_exceptions
print run_feature_tests(configurations=[DefaultConfiguration,
                                           GeNNConfiguration], feature_tests=[NeuronGroupIntegrationLinear, NeuronGroupIntegrationEuler, NeuronGroupLIF, SynapsesPre, SynapsesPost]).tables_and_exceptions
