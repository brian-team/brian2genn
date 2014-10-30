// define the time step
{{ dtDef }}

#include <inttypes.h>
#include "modelSpec.h"
#include "modelSpec.cc"

//--------------------------------------------------------------------------
/*! \brief This function defines the {{model_name}} model 
*/
//--------------------------------------------------------------------------


// define the neuron model types as integer variables
{% for neuron_model in neuron_models %}
unsigned int {{neuron_model.name}}NEURON;
{% endfor %}
{% for synapse_model in synapse_models %}
unsigned int {{synapse_model.name}}WEIGHTUPDATE;
unsigned int {{synapse_model.name}}POSTSYN;
unsigned int {{synapse_model.name}}SYNDYN;
{% endfor %}

// parameter values
// neurons
{% for neuron_model in neuron_models %}
float {{neuron_model.name}}_p[{{neuron_model.pvalue.__len__()}}]= {
  {% for k in neuron_model.pvalue %} {{k}},
  {% endfor %}
};

{% endfor %}

// synapses
{% for synapse_model in synapse_models %}
float {{synapse_model.name}}_p[{{synapse_model.pvalue.__len__()}}]= {
  {% for k in synapse_model.pvalue %} {{k}},
  {% endfor %}
};

float {{synapse_model.name}}_postsynp[{{synapse_model.postsyn_pvalue.__len__()}}]= {
  {% for k in synapse_model.postsyn_pvalue %} {{k}},
  {% endfor %}
};

{% endfor %}

// initial variables (neurons)
{% for neuron_model in neuron_models %}
float {{neuron_model.name}}_ini[{{neuron_model.variables.__len__()}}]= {
  {% for k in neuron_model.variables %} 0.0,
  {% endfor %}
};

{% endfor %}
 
// initial variables (synapses)
{% for synapse_model in synapse_models %}
float {{synapse_model.name}}_ini[{{synapse_model.variables.__len__()}}]= {
  {% for k in synapse_model.variables %} 0.0,
  {% endfor %}
};

float {{synapse_model.name}}_postsyn_ini[{{synapse_model.postsyn_variables.__len__()}}]= {
  {% for k in synapse_model.postsyn_variables %} 0.0,
  {% endfor %}
};

{% endfor %}
 

void modelDefinition(NNmodel &model)
{
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
  s.varNames.push_back(tS("_hidden_weightmatrix"));
  {% for var in synapse_model.variabletypes %}
  s.varTypes.push_back(tS("{{var}}"));
  {% endfor %}
  s.varTypes.push_back(tS("char"));
  // step2: add parameters
  {% for par in synapse_model.parameters %}
  s.pNames.push_back(tS("{{par}}"));
  {% endfor %}
  // step 3: add simcode
  s.simCode= tS("{% for line in synapse_model.simCode %}{{line}}{% endfor %}");
  s.simLearnPost= tS("{% for line in synapse_model.simLearnPost %}{{line}}{% endfor %}");
  s.synapseDynamics= tS("{% for line in synapse_model.synapseDynamics %}{{line}}{% endfor %}");  weightUpdateModels.push_back(s);
  {{synapse_model.name}}WEIGHTUPDATE= weightUpdateModels.size()+MAXSYN-1;
  // post-synaptic model
  ps.varNames.clear();
  ps.varTypes.clear();
  ps.pNames.clear(); 
  ps.dpNames.clear();
  {% for var in synapse_model.postsyn_variables %}
  ps.varNames.push_back(tS("{{var}}"));
  {% endfor %}
  {% for var in synapse_model.postsyn_variabletypes %}  
  ps.varTypes.push_back(tS("{{var}}"));
  {% endfor %}
  {% for par in synapse_model.postsyn_parameters %}
  ps.pNames.push_back(tS("{{par}}"));
  {% endfor %}
  ps.postSyntoCurrent= tS("{% for line in synapse_model.postSyntoCurrent %}{{line}}{% endfor %}");
  postSynModels.push_back(ps); 
  {{synapse_model.name}}POSTSYN= postSynModels.size()-1;  
  {% endfor %}

  model.setName("{{model_name}}");
  model.setPrecision(DOUBLE);
  {% for neuron_model in neuron_models %} 
  model.addNeuronPopulation("{{neuron_model.name}}", {{neuron_model.N}}, {{neuron_model.name}}NEURON, {{neuron_model.name}}_p, {{neuron_model.name}}_ini);
  {% endfor %}
  {% for synapse_model in synapse_models %} 
// TODO: Consider felxible use of DENSE and SPARSE (but beware of difficulty of judging which to use at compile time)
  model.addSynapsePopulation("{{synapse_model.name}}", {{synapse_model.name}}WEIGHTUPDATE, DENSE, INDIVIDUALG, NO_DELAY, {{synapse_model.name}}POSTSYN, "{{synapse_model.srcname}}", "{{synapse_model.trgname}}", {{synapse_model.name}}_ini, {{synapse_model.name}}_p, {{synapse_model.name}}_postsyn_ini, {{synapse_model.name}}_postsynp);
  {% endfor %}

}

