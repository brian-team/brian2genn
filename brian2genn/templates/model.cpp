// define the time step

#include <stdint.h>
#include "modelSpec.h"
#include "global.h"

//--------------------------------------------------------------------------
/*! \brief This function defines the {{model_name}} model 
*/
//--------------------------------------------------------------------------

// 
// define the neuron model types as integer variables
{% for neuron_model in neuron_models %}
unsigned int {{neuron_model.name}}NEURON;
{% endfor %}
{% for synapse_model in synapse_models %}
unsigned int {{synapse_model.name}}WEIGHTUPDATE;
unsigned int {{synapse_model.name}}POSTSYN;
{% endfor %}

// parameter values
// neurons
{% for neuron_model in neuron_models %}
{% if neuron_model.pvalue.__len__() == 0 %}
double *{{neuron_model.name}}_p= NULL;
{% else %}
double {{neuron_model.name}}_p[{{neuron_model.pvalue.__len__()}}]= {
  {% for k in neuron_model.pvalue %} {{k}},
  {% endfor %}
};
{% endif %}
{% endfor %}

// synapses
{% for synapse_model in synapse_models %}
{% if synapse_model.pvalue.__len__() == 0 %}
double *{{synapse_model.name}}_p= NULL;
{% else %}
double {{synapse_model.name}}_p[{{synapse_model.pvalue.__len__()}}]= {
  {% for k in synapse_model.pvalue %} {{k}},
  {% endfor %}
};
{% endif %}

double *{{synapse_model.name}}_postsynp= NULL;

{% endfor %}

// initial variables (neurons)
{% for neuron_model in neuron_models %}
double {{neuron_model.name}}_ini[{{neuron_model.variables.__len__()+1}}]= {
  {% for k in neuron_model.variables %} 0.0,
  {% endfor %}
  0.0
};
{% endfor %}
 
// initial variables (synapses)
// one additional initial variable for hidden_weightmatrix
{% for synapse_model in synapse_models %}
double {{synapse_model.name}}_ini[{{synapse_model.variables.__len__()+1}}]= {
  {% for k in synapse_model.variables %} 0.0,
  {% endfor %}
  {% if synapse_model.connectivity == 'DENSE' %}
  0.0
  {% endif %}
};

double *{{synapse_model.name}}_postsyn_ini= NULL;
{% endfor %}
 

void modelDefinition(NNmodel &model)
{
  initGeNN();
  GENN_PREFERENCES::autoRefractory = 0;
  // Compiler optimization flags
  GENN_PREFERENCES::userCxxFlagsWIN = "{{compile_args_msvc}}";
  GENN_PREFERENCES::userCxxFlagsGNU = "{{compile_args_gcc}}";
  GENN_PREFERENCES::userNvccFlags = "{{compile_args_nvcc}}";

  {{ dtDef }}
  // Define the relevant neuron models
  neuronModel n;

  {% for neuron_model in neuron_models %}
  // step 1: add variables
  n.varNames.clear();
  n.varTypes.clear();
  {% for var in neuron_model.variables %}
  n.varNames.push_back("{{var}}");
  {% endfor %}
  {% for var in neuron_model.variabletypes %}
  n.varTypes.push_back("{{var}}");
  {% endfor %}
  // step 2: add scalar (shared) variables
  n.extraGlobalNeuronKernelParameters.clear();
  n.extraGlobalNeuronKernelParameterTypes.clear();
  {% for var in neuron_model.shared_variables %}
  n.extraGlobalNeuronKernelParameters.push_back("{{var}}");
  {% endfor %}
  {% for vartype in neuron_model.shared_variabletypes %}
  n.extraGlobalNeuronKernelParameterTypes.push_back("{{vartype}}");
  {% endfor %}
  // step 3: add parameters
  n.pNames.clear(); 
  {% for par in neuron_model.parameters %}
  n.pNames.push_back("{{par}}");
  {% endfor %}
  // step 4: add simcode
  n.simCode= "{% for line in neuron_model.code_lines %}{{line}}{% endfor %}";
  // step 5: add thresholder code
  n.thresholdConditionCode= "{% for line in neuron_model.thresh_cond_lines %}{{line}}{% endfor %}";
  // step 6: add resetter code
  n.resetCode= "{% for line in neuron_model.reset_code_lines %}{{line}}{% endfor %}";
  // step 7: add support code
  n.supportCode= "{% for line in neuron_model.support_code_lines %}{{line}}{% endfor %}";
  nModels.push_back(n);
  {{neuron_model.name}}NEURON= nModels.size()-1;
  {% endfor %}

  weightUpdateModel s;
  postSynModel ps;  
  {% for synapse_model in synapse_models %}
  // synaptic model
  s.varNames.clear();
  s.varTypes.clear();
  s.pNames.clear(); 
  s.dpNames.clear();
  // step 1: variables
  {% for var in synapse_model.variables %}
  s.varNames.push_back("{{var}}");
  {% endfor %}
  {% if synapse_model.connectivity == 'DENSE' %} 
  s.varNames.push_back("_hidden_weightmatrix");
  {% endif %}
  {% for var in synapse_model.variabletypes %}
  s.varTypes.push_back("{{var}}");
  {% endfor %}
  {% if synapse_model.connectivity == 'DENSE' %} 
  s.varTypes.push_back("char");
  {% endif %}
  // step 2: scalar (shared) variables
  s.extraGlobalSynapseKernelParameters.clear();
  s.extraGlobalSynapseKernelParameterTypes.clear();
  {% for var in synapse_model.shared_variables %}
  s.extraGlobalSynapseKernelParameters.push_back("{{var}}");
  {% endfor %}
  {% for vartype in synapse_model.shared_variabletypes %}
  s.extraGlobalSynapseKernelParameterTypes.push_back("{{vartype}}");
  {% endfor %}
  // step 3: add parameters
  {% for par in synapse_model.parameters %}
  s.pNames.push_back("{{par}}");
  {% endfor %}
  // step 4: add simcode
  s.simCode= "{% for line in synapse_model.main_code_lines['pre'] %}{{line}}{% endfor %}";
  s.simLearnPost= "{% for line in synapse_model.main_code_lines['post'] %}{{line}}{% endfor %}";
  s.synapseDynamics= "{% for line in synapse_model.main_code_lines['dynamics'] %}{{line}}{% endfor %}";
  s.simCode_supportCode= "{% for line in synapse_model.support_code_lines['pre'] %}{{line}}{% endfor %}";
  s.simLearnPost_supportCode= "{% for line in synapse_model.support_code_lines['post'] %}{{line}}{% endfor %}";
  s.synapseDynamics_supportCode= "{% for line in synapse_model.support_code_lines['dynamics'] %}{{line}}{% endfor %}";
  weightUpdateModels.push_back(s);
  {{synapse_model.name}}WEIGHTUPDATE= weightUpdateModels.size()-1;
  // post-synaptic model
  ps.varNames.clear();
  ps.varTypes.clear();
  ps.pNames.clear(); 
  ps.dpNames.clear();
  ps.postSyntoCurrent= "{% for line in synapse_model.postSyntoCurrent %}{{line}}{% endfor %}";
  postSynModels.push_back(ps); 
  {{synapse_model.name}}POSTSYN= postSynModels.size()-1;  
  {% endfor %}

  model.setName("{{model_name}}");
  model.setPrecision(GENN_DOUBLE);
  {% for neuron_model in neuron_models %} 
  model.addNeuronPopulation("{{neuron_model.name}}", {{neuron_model.N}}, {{neuron_model.name}}NEURON, {{neuron_model.name}}_p, {{neuron_model.name}}_ini);
  {% endfor %}
  {% for spikeGen_model in spikegenerator_models %} 
  model.addNeuronPopulation("{{spikeGen_model.name}}", {{spikeGen_model.N}}, SPIKESOURCE, NULL, NULL);
  {% endfor %}
  unsigned int delaySteps;
  {% for synapse_model in synapse_models %} 
// TODO: Consider felxible use of DENSE and SPARSE (but beware of difficulty of judging which to use at compile time)
  {% if synapse_model.delay == 0 %}
  delaySteps = NO_DELAY;
  {% else %}
  delaySteps = {{synapse_model.delay}};
  {% endif %}
  model.addSynapsePopulation("{{synapse_model.name}}", {{synapse_model.name}}WEIGHTUPDATE, {{synapse_model.connectivity}}, INDIVIDUALG, delaySteps, {{synapse_model.name}}POSTSYN, "{{synapse_model.srcname}}", "{{synapse_model.trgname}}", {{synapse_model.name}}_ini, {{synapse_model.name}}_p, {{synapse_model.name}}_postsyn_ini, {{synapse_model.name}}_postsynp);
  {% endfor %}
  model.finalize();
}

