// define the time step

#include <stdint.h>
#include "modelSpec.h"
#include "brianlib/randomkit/randomkit.cc"

#include "objects.h"
#include "objects.cpp"

{% for header in header_files %}
{% if header.startswith('"') or header.startswith('<') %}
#include {{header}}
{% else %}
#include "{{header}}"
{% endif %}
{% endfor %}

// We need these to compile objects.cpp, but they are only used in _write_arrays which we never call.
double Network::_last_run_time = 0.0;
double Network::_last_run_completed_fraction = 0.0;

{% for inc in codeobj_inc %}
{{inc}}
{% endfor %}

{% for inc in max_row_length_include %}
{{inc}}
{% endfor %}

//--------------------------------------------------------------------------
/*! \brief This function defines the Brian2GeNN_model
*/
//--------------------------------------------------------------------------

//
// define the neuron model classes

{% for neuron_model in neuron_models %}
class {{neuron_model.name}}NEURON : public NeuronModels::Base
{
public:
    DECLARE_MODEL({{neuron_model.name}}NEURON, {{neuron_model.pvalue.__len__()}}, {{neuron_model.variables.__len__()}});

    SET_SIM_CODE("{% for line in neuron_model.code_lines %}{{line}}{% endfor %}");
    SET_THRESHOLD_CONDITION_CODE("{% for line in neuron_model.thresh_cond_lines %}{{line}}{% endfor %}");
    SET_RESET_CODE("{% for line in neuron_model.reset_code_lines %}{{line}}{% endfor %}");

    SET_SUPPORT_CODE("{% for line in neuron_model.support_code_lines %}{{line}}{% endfor %}");

    SET_PARAM_NAMES({
    {% for par in neuron_model.parameters %}
        "{{par}}"{% if not loop.last %},{% endif %}
    {% endfor %}
    });
    SET_VARS({
    {% for var, type in zip(neuron_model.variables, neuron_model.variabletypes) %}
        {"{{var}}", "{{type}}"}{% if not loop.last %},{% endif %}
    {% endfor %}
    });
    SET_EXTRA_GLOBAL_PARAMS({
    {% for var,type in zip(neuron_model.shared_variables, neuron_model.shared_variabletypes) %}
        {"{{var}}", "{{type}}"}{% if not loop.last %},{% endif %}
    {% endfor %}
    });
    SET_NEEDS_AUTO_REFRACTORY(false);
};
IMPLEMENT_MODEL({{neuron_model.name}}NEURON);
{% endfor %}

//
// define the synapse model classes
{% for synapse_model in synapse_models %}
class {{synapse_model.name}}WEIGHTUPDATE : public WeightUpdateModels::Base
{
public:
    DECLARE_MODEL({{synapse_model.name}}WEIGHTUPDATE, {{synapse_model.pvalue.__len__()}}, {{synapse_model.variables.__len__() + (1 if synapse_model.connectivity == 'DENSE' else 0)}});

    SET_SIM_CODE("{% for line in synapse_model.main_code_lines['pre'] %}{{line}}{% endfor %}");
    SET_LEARN_POST_CODE("{% for line in synapse_model.main_code_lines['post'] %}{{line}}{% endfor %}");
    SET_SYNAPSE_DYNAMICS_CODE("{% for line in synapse_model.main_code_lines['dynamics'] %}{{line}}{% endfor %}");

    SET_SIM_SUPPORT_CODE("{% for line in synapse_model.support_code_lines['pre'] %}{{line}}{% endfor %}");
    SET_LEARN_POST_SUPPORT_CODE("{% for line in synapse_model.support_code_lines['post'] %}{{line}}{% endfor %}");
    SET_SYNAPSE_DYNAMICS_SUPPORT_CODE("{% for line in synapse_model.support_code_lines['dynamics'] %}{{line}}{% endfor %}");

    SET_PARAM_NAMES({
    {% for par in synapse_model.parameters %}
        "{{par}}"{% if not loop.last %},{% endif %}
    {% endfor %}
    });

    SET_VARS({
    {% for var, type in zip(synapse_model.variables, synapse_model.variabletypes) %}
        {"{{var}}", "{{type}}"}{% if not loop.last %},{% endif %}
    {% endfor %}
    {% if synapse_model.connectivity == 'DENSE' %}
        ,{"_hidden_weightmatrix", "char"}
    {% endif %}
    });

    SET_EXTRA_GLOBAL_PARAMS({
    {% for var, type in zip(synapse_model.shared_variables, synapse_model.shared_variabletypes) %}
        {"{{var}}", "{{type}}"}{% if not loop.last %},{% endif %}
    {% endfor %}
    });

    //SET_NEEDS_PRE_SPIKE_TIME(true);
    //SET_NEEDS_POST_SPIKE_TIME(true);

};

IMPLEMENT_MODEL({{synapse_model.name}}WEIGHTUPDATE);

class {{synapse_model.name}}POSTSYN : public PostsynapticModels::Base
{
public:
    DECLARE_MODEL({{synapse_model.name}}POSTSYN, 0, 0);

    SET_APPLY_INPUT_CODE("$(Isyn) += {% for line in synapse_model.postSyntoCurrent %}{{line}}{% endfor %};");
};
IMPLEMENT_MODEL({{synapse_model.name}}POSTSYN);
{% endfor %}

// parameter values
// neurons
{% for neuron_model in neuron_models %}
{{neuron_model.name}}NEURON::ParamValues {{neuron_model.name}}_p
{% if neuron_model.pvalue.__len__() > 0 %}
(
{% for k in neuron_model.pvalue %}
    {{k}}{% if not loop.last %},{% endif %}
{% endfor %}
){% endif %};
{% endfor %}

// synapses
{% for synapse_model in synapse_models %}
{{synapse_model.name}}WEIGHTUPDATE::ParamValues {{synapse_model.name}}_p
{% if synapse_model.pvalue.__len__() > 0 %}
(
{% for k in synapse_model.pvalue %}
    {{k}}{% if not loop.last %},{% endif %}
{% endfor %}
){% endif %};
{% endfor %}

// initial variables (neurons)
{% for neuron_model in neuron_models %}
{{neuron_model.name}}NEURON::VarValues {{neuron_model.name}}_ini
{% if neuron_model.variables.__len__() > 0 %}
(
    {% for k in neuron_model.variables %}
    uninitialisedVar(){% if not loop.last %},{% endif %}
    {% endfor %}
){% endif %};
{% endfor %}
 
// initial variables (synapses)
// one additional initial variable for hidden_weightmatrix
{% for synapse_model in synapse_models %}
{{synapse_model.name}}WEIGHTUPDATE::VarValues {{synapse_model.name}}_ini
{% if synapse_model.variables.__len__() > 0 or synapse_model.connectivity == 'DENSE' %}
(
    {% for k in synapse_model.variables %}
    uninitialisedVar(){% if not loop.last %},{% endif %}
    {% endfor %}
    {% if synapse_model.connectivity == 'DENSE' %}
    ,uninitialisedVar()
    {% endif %}
){% endif %};
{% endfor %}


void modelDefinition(NNmodel &model)
{
  _init_arrays();
  _load_arrays();
  {{'\n'.join(code_lines['before_start'])|autoindent}}
  rk_randomseed(brian::_mersenne_twister_states[0]);
  {{'\n'.join(code_lines['after_start'])|autoindent}}
  {
	  using namespace brian;
	  {{ main_lines | autoindent }}
  }

  {% for max_row_length in max_row_length_run_calls %}
  {{max_row_length}}
  {% endfor %}

  {% for synapses in max_row_length_synapses %}
  const long maxRow{{synapses}}= std::max(*std::max_element(brian::_dynamic_array_{{synapses}}_N_outgoing.begin(),brian::_dynamic_array_{{synapses}}_N_outgoing.end()),1);
  const long maxCol{{synapses}}= std::max(*std::max_element(brian::_dynamic_array_{{synapses}}_N_incoming.begin(),brian::_dynamic_array_{{synapses}}_N_incoming.end()),1);
  {% endfor %}
  
    {% if use_GPU %}
    // GENN_PREFERENCES set in brian2genn
    GENN_PREFERENCES.deviceSelectMethod = DeviceSelect::{{prefs['devices.genn.cuda_backend.device_select']}};
    {% if prefs['devices.genn.cuda_backend.device_select'] == 'MANUAL' %}
    GENN_PREFERENCES.manualDeviceID = {{prefs['devices.genn.cuda_backend.manual_device']}};
    {% endif %}
    GENN_PREFERENCES.blockSizeSelectMethod = BlockSizeSelect::{{prefs['devices.genn.cuda_backend.blocksize_select_method']}};

    {% if prefs['devices.genn.cuda_backend.blocksize_select_method'] == 'MANUAL' %}
    GENN_PREFERENCES.manualBlockSizes = {
        {{prefs['devices.genn.cuda_backend.neuron_blocksize']}},
        {{prefs['devices.genn.cuda_backend.synapse_blocksize']}},
        {{prefs['devices.genn.cuda_backend.synapse_blocksize']}},
        {{prefs['devices.genn.cuda_backend.learning_blocksize']}},
        {{prefs['devices.genn.cuda_backend.synapse_dynamics_blocksize']}},
        {{prefs['devices.genn.cuda_backend.init_blocksize']}},
        {{prefs['devices.genn.cuda_backend.init_sparse_blocksize']}},
        {{prefs['devices.genn.cuda_backend.pre_neuron_reset_blocksize']}},
        {{prefs['devices.genn.cuda_backend.pre_synapse_reset_blocksize']}}};
    {% endif %}
    GENN_PREFERENCES.userNvccFlags = "{{' '.join(prefs['devices.genn.cuda_backend.extra_compile_args_nvcc'])}}";
    {% endif %}

    {{ dtDef }}

    model.setName("magicnetwork_model");
    model.setPrecision({{precision}});
    {% if precision == 'GENN_FLOAT' %}
    model.setTimePrecision(TimePrecision::DOUBLE);
    {% endif %}
    {% if profiled %}
    model.setTiming(true);
    {% endif %}
    {% for neuron_model in neuron_models %}
    model.addNeuronPopulation<{{neuron_model.name}}NEURON>("{{neuron_model.name}}", {{neuron_model.N}}, {{neuron_model.name}}_p, {{neuron_model.name}}_ini);
    {% endfor %}
    {% for spikeGen_model in spikegenerator_models %}
    model.addNeuronPopulation<NeuronModels::SpikeSource>("{{spikeGen_model.name}}", {{spikeGen_model.N}}, {}, {});
    {% endfor %}
    {% for synapse_model in synapse_models %}
    {
    // TODO: Consider flexible use of DENSE and SPARSE (but beware of difficulty of judging which to use at compile time)
    {% if synapse_model.delay == 0 %}
    const unsigned int delaySteps = NO_DELAY;
    {% else %}
    const unsigned int delaySteps = {{synapse_model.delay}};
    {% endif %}
    auto *syn = model.addSynapsePopulation<{{synapse_model.name}}WEIGHTUPDATE, {{synapse_model.name}}POSTSYN>(
        "{{synapse_model.name}}", SynapseMatrixType::{{synapse_model.connectivity}}_INDIVIDUALG, delaySteps,
        "{{synapse_model.srcname}}", "{{synapse_model.trgname}}",
        {{synapse_model.name}}_p, {{synapse_model.name}}_ini,
        {}, {});
    syn->setSpanType(SynapseGroup::SpanType::{{prefs['devices.genn.synapse_span_type']}});
    {% if synapse_model.connectivity == 'SPARSE' %}
    syn->setMaxConnections(maxRow{{synapse_model.name}});
    syn->setMaxSourceConnections(maxCol{{synapse_model.name}});
    {% endif %}
    }
    {% endfor %}
}

