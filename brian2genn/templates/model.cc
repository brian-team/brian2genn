// define the time step
{{ dtDef }}

#include <stdint.h>
#include "modelSpec.h"
#include "modelSpec.cc"


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
  GENN_PREFERENCES::autoRefractory= 0;
  // Define the relevant neuron models
  neuronModel n;

  {% for neuron_model in neuron_models %}
  // setp 1: add variables
  n.varNames.clear();
  n.varTypes.clear();
  {% for var in neuron_model.variables %}
  n.varNames.push_back(tS("{{var}}"));
  {% endfor %}
  {% for var in neuron_model.variabletypes %}
  n.varTypes.push_back(tS("{{var}}"));
  {% endfor %}
  // step2: add parameters
  n.pNames.clear(); 
  {% for par in neuron_model.parameters %}
  n.pNames.push_back(tS("{{par}}"));
  {% endfor %}
  // step 3: add simcode
  n.simCode= tS("{% for line in neuron_model.code_lines %}{{line}}{% endfor %}");
  // step 4: add thresholder code
  n.thresholdConditionCode= tS("{% for line in neuron_model.thresh_cond_lines %}{{line}}{% endfor %}");
  // step 5: add resetter code
  n.resetCode= tS("{% for line in neuron_model.reset_code_lines %}{{line}}{% endfor %}");
  // step 6: add support code
  n.supportCode= tS("{% for line in neuron_model.support_code_lines %}{{line}}{% endfor %}");
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
  {% for var in synapse_model.variables %}
  s.varNames.push_back(tS("{{var}}"));
  {% endfor %}
  {% if synapse_model.connectivity == 'DENSE' %} 
  s.varNames.push_back(tS("_hidden_weightmatrix"));
  {% endif %}
  {% for var in synapse_model.variabletypes %}
  s.varTypes.push_back(tS("{{var}}"));
  {% endfor %}
  {% if synapse_model.connectivity == 'DENSE' %} 
  s.varTypes.push_back(tS("char"));
  {% endif %}
  // step2: add parameters
  {% for par in synapse_model.parameters %}
  s.pNames.push_back(tS("{{par}}"));
  {% endfor %}
  // step 3: add simcode
  s.simCode= tS("{% for line in synapse_model.simCode %}{{line}}{% endfor %}");
  s.simLearnPost= tS("{% for line in synapse_model.simLearnPost %}{{line}}{% endfor %}");
  s.synapseDynamics= tS("{% for line in synapse_model.synapseDynamics %}{{line}}{% endfor %}");  
  s.simCode_supportCode= tS("{% for line in synapse_model.pre_support_code_lines %}{{line}}{% endfor %}");  
   s.simLearnPost_supportCode= tS("{% for line in synapse_model.post_support_code_lines %}{{line}}{% endfor %}");  
   s.synapseDynamics_supportCode= tS("{% for line in synapse_model.dyn_support_code_lines %}{{line}}{% endfor %}");  
  weightUpdateModels.push_back(s);
  {{synapse_model.name}}WEIGHTUPDATE= weightUpdateModels.size()-1;
  // post-synaptic model
  ps.varNames.clear();
  ps.varTypes.clear();
  ps.pNames.clear(); 
  ps.dpNames.clear();
  ps.postSyntoCurrent= tS("{% for line in synapse_model.postSyntoCurrent %}{{line}}{% endfor %}");
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
  {% for synapse_model in synapse_models %} 
// TODO: Consider felxible use of DENSE and SPARSE (but beware of difficulty of judging which to use at compile time)
  model.addSynapsePopulation("{{synapse_model.name}}", {{synapse_model.name}}WEIGHTUPDATE, {{synapse_model.connectivity}}, INDIVIDUALG, NO_DELAY, {{synapse_model.name}}POSTSYN, "{{synapse_model.srcname}}", "{{synapse_model.trgname}}", {{synapse_model.name}}_ini, {{synapse_model.name}}_p, {{synapse_model.name}}_postsyn_ini, {{synapse_model.name}}_postsynp);
  {% endfor %}
  model.finalize();
}

