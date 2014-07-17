// define the time step
{{ dtDef }}

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

// parameter values
{% for neuron_model in neuron_models %}
float {{neuron_model.name}}_p[{{neuron_model.pvalue.__len__()}}]= {
  {% for k in neuron_model.pvalue %} {{k}},
  {% endfor %}
};

{% endfor %}

// initial variables
{% for neuron_model in neuron_models %}
float {{neuron_model.name}}_ini[{{neuron_model.variables.__len__()}}]= {
  {% for k in neuron_model.variables %} 0.0,
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
  n.varNames.push_back(tS("{{var[0]}}"));
  n.varTypes.push_back(tS("{{var[1]}}"));
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
  cerr << nModels.size() << endl;
  {% endfor %}
  
  model.setName("{{model_name}}");
  model.setPrecision(DOUBLE);
  {% for neuron_model in neuron_models %} 
  model.addNeuronPopulation("{{neuron_model.name}}", {{neuron_model.N}}, {{neuron_model.name}}NEURON, {{neuron_model.name}}_p, {{neuron_model.name}}_ini);
  {% endfor %}
}

