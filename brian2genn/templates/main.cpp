{% macro cpp_file() %}
//--------------------------------------------------------------------------
/*! \file main.cu

\brief Main entry point for the running a model simulation. 
*/
//--------------------------------------------------------------------------

#include "main.h"
#include "magicnetwork_model_CODE/definitions.h"

{% for header in header_files %}
{% if header.startswith('"') or header.startswith('<') %}
#include {{header}}
{% else %}
#include "{{header}}"
{% endif %}
{% endfor %}

#include "engine.cpp"



//--------------------------------------------------------------------------
/*! \brief This function is the entry point for running the simulation of the MBody1 model network.
*/
//--------------------------------------------------------------------------
int main(int argc, char *argv[])
{
  if (argc != 3)
  {
    fprintf(stderr, "usage: main <basename> <time (s)> \n");
    return 1;
  }
  double totalTime= atof(argv[2]);
  string OutDir = std::string(argv[1]) +"_output";
  string cmd= std::string("mkdir ") +OutDir;
  system(cmd.c_str());
  string name;
  {% if profiled %}
  name= OutDir+ "/"+ argv[1] + ".time";
  FILE *timef= fopen(name.c_str(),"a");
  {% endif %}
  fprintf(stderr, "# DT %g \n", DT);
  fprintf(stderr, "# totalTime %f \n", totalTime);

  {{'\n'.join(code_lines['before_start'])|autoindent}}

  //-----------------------------------------------------------------
  // build the neuronal circuitery (calls initialize and allocateMem)
  engine eng;

  //-----------------------------------------------------------------
  // load variables and parameters and translate them from Brian to Genn
  _init_arrays();
  _load_arrays();
  rk_randomseed(brian::_mersenne_twister_states[0]);
  {{'\n'.join(code_lines['after_start'])|autoindent}}
  {
	  using namespace brian;
	  {{ main_lines | autoindent }}
  }

  // translate to GeNN synaptic arrays
  {% for synapses in synapse_models %}
  {% if synapses.connectivity == 'DENSE' %}
  {% for var in synapses.variables %}
  {% if synapses.variablescope[var] == 'brian' %}
  convert_dynamic_arrays_2_dense_matrix(brian::_dynamic_array_{{synapses.name}}__synaptic_pre, brian::_dynamic_array_{{synapses.name}}__synaptic_post, brian::_dynamic_array_{{synapses.name}}_{{var}}, {{var}}{{synapses.name}}, {{synapses.srcN}}, {{synapses.trgN}});
  {% endif %}
  {% endfor %} {# all synapse variables #}
  create_hidden_weightmatrix(brian::_dynamic_array_{{synapses.name}}__synaptic_pre, brian::_dynamic_array_{{synapses.name}}__synaptic_post, _hidden_weightmatrix{{synapses.name}},{{synapses.srcN}}, {{synapses.trgN}});
  {% else %} {# for sparse matrix representations #}
  initialize_sparse_synapses(brian::_dynamic_array_{{synapses.name}}__synaptic_pre, brian::_dynamic_array_{{synapses.name}}__synaptic_post,
                             rowLength{{synapses.name}}, ind{{synapses.name}}, maxRowLength{{synapses.name}},
                             {{synapses.srcN}}, {{synapses.trgN}},
                             sparseSynapseIndices{{synapses.name}});
  {% for var in synapses.variables %}
  {% if synapses.variablescope[var] == 'brian' %}
  convert_dynamic_arrays_2_sparse_synapses(brian::_dynamic_array_{{synapses.name}}_{{var}},
					   sparseSynapseIndices{{synapses.name}},
                                           {{var}}{{synapses.name}},
                                           {{synapses.srcN}}, {{synapses.trgN}});
  {% endif %}
  {% endfor %} {# all synapse variables #}
  {% endif %} {# dense/sparse #}
  {% for var in synapses.shared_variables %}
  std::copy_n(brian::_array_{{synapses.name}}_{{var}}, 1, &{{var}}{{synapses.name}});
  {% endfor %} {# shared variables #}
  {% endfor %} {# all synapse_models #}

  // copy variable arrays
  {% for neuron in neuron_models %} 
  {% for var in neuron.variables %}
  {% if neuron.variablescope[var] == 'brian' %}
  std::copy_n(brian::_array_{{neuron.name}}_{{var}}, {{neuron.N}}, {{var}}{{neuron.name}});
  {% endif %}
  {% endfor %}
  {% endfor %}

  // copy scalar variables
  {% for neuron in neuron_models %}
  {% for var in neuron.shared_variables %}
  std::copy_n(brian::_array_{{neuron.name}}_{{var}}, 1, &{{var}}{{neuron.name}});
  {% endfor %}
  {% endfor %}
  
  // initialise random seeds (if any are used)
  {% for neuron in neuron_models %} ;
  {% if '_seed' in neuron.variables %}
  for (unsigned int i= 0; i < {{neuron.N}}; i++) {
      _seed{{neuron.name}}[i]= (uint64_t) (rand()*0x0000FFFFFFFFFFFFLL);
  }
  {% endif %}
  {% endfor %}
  {% for synapses in synapse_models %}
  {% if '_seed' in synapses.variables %}
  for (unsigned int i= 0; i < (maxRowLength{{synapses.name}} * {{synapses.srcN}}); i++) {
      _seed{{synapses.name}}[i]= (uint64_t) (rand()*0x0000FFFFFFFFFFFFLL);
  }
  {% endif %}
  {% endfor %}

  // Perform final stage of initialization, uploading manually initialized variables to GPU etc
  initializeSparse();
  
  //------------------------------------------------------------------
  // output general parameters to output file and start the simulation
  fprintf(stderr, "# We are running with fixed time step %f \n", DT);

  t= 0.;
  void *devPtr;
  {{'\n'.join(code_lines['before_network_run'])|autoindent}}
  eng.run(totalTime); // run for the full duration
  {{'\n'.join(code_lines['after_network_run'])|autoindent}}
  cerr << t << " done ..." << endl;
  {% if profiled %}
  {% for kt in ('neuronUpdateTime', 'presynapticUpdateTime', 'postsynapticUpdateTime', 'synapseDynamicsTime', 'initTime', 'initSparseTime') %}
  fprintf(timef,"%f ", {{kt}});
  {% endfor %}
  fprintf(timef,"\n");
  {% endif %} 

  // get the final results from the GPU 
  eng.getStateFromGPU();
  eng.getSpikesFromGPU();

  // translate GeNN arrays back to synaptic arrays
  {% for synapses in synapse_models %}
  {% if synapses.connectivity == 'DENSE' %}
  {% for var in synapses.variables %}
  {% if synapses.variablescope[var] == 'brian' %}
  convert_dense_matrix_2_dynamic_arrays({{var}}{{synapses.name}}, {{synapses.srcN}}, {{synapses.trgN}},brian::_dynamic_array_{{synapses.name}}__synaptic_pre, brian::_dynamic_array_{{synapses.name}}__synaptic_post, brian::_dynamic_array_{{synapses.name}}_{{var}});
  {% endif %}
  {% endfor %} {# all synapse variables #}
  {% else %} {# for sparse matrix representations #} 
  {% set _first_var = true %}
  {% for var in synapses.variables %}
  {% if synapses.variablescope[var] == 'brian' %}
      {% if _first_var %}
      {% set _mode = 'b2g::FULL_MONTY' %}
      {% set _first_var = false %}
      {% else %}
      {% set _mode = 'b2g::COPY_ONLY' %}
      {% endif %}
      convert_sparse_synapses_2_dynamic_arrays(rowLength{{synapses.name}}, ind{{synapses.name}}, maxRowLength{{synapses.name}},
                                               {{var}}{{synapses.name}}, {{synapses.srcN}}, {{synapses.trgN}}, brian::_dynamic_array_{{synapses.name}}__synaptic_pre, brian::_dynamic_array_{{synapses.name}}__synaptic_post, brian::_dynamic_array_{{synapses.name}}_{{var}}, {{_mode}});
  {% endif %}
  {% endfor %} {# all synapse variables #}
  {% endif %} {# dense/sparse #}
  {% for var in synapses.shared_variables %}
  std::copy_n(&{{var}}{{synapses.name}}, 1, brian::_array_{{synapses.name}}_{{var}});
  {% endfor %} {# shared variables #}
  {% endfor %} {# all synapse_models #}

  // copy variable arrays
  {% for neuron in neuron_models %} 
  {% for var in neuron.variables %}
  {% if neuron.variablescope[var] == 'brian' %}
  std::copy_n({{var}}{{neuron.name}}, {{neuron.N}}, brian::_array_{{neuron.name}}_{{var}});
  {% endif %}
  {% endfor %}
  {% endfor %}

  // copy scalar variables
  {% for neuron in neuron_models %}
  {% for var in neuron.shared_variables %}
  std::copy_n(&{{var}}{{neuron.name}}, 1, brian::_array_{{neuron.name}}_{{var}});
  {% endfor %}
  {% endfor %}

  {{'\n'.join(code_lines['before_end'])|autoindent}}
  _write_arrays();
  _dealloc_arrays();
  {{'\n'.join(code_lines['after_end'])|autoindent}}
  cerr << "everything finished." << endl;
  return 0;
}

{% endmacro %}

{% macro h_file() %}
//--------------------------------------------------------------------------
/*! \file main.h

\brief Header file containing global variables and macros used in running the model.
*/
//--------------------------------------------------------------------------

using namespace std;
#include <cassert>
#include <cstdint>
#include <vector>

// we will hard-code some stuff ... because at the end of the day that is 
// what we will do for the CUDA version

#define DBG_SIZE 10000


//----------------------------------------------------------------------
// other stuff:
// These variables (if any) are needed to be able to efficiently copy brian
// synapse variables into genn SPARSE synaptic arrays (needed for run_regularly)

{% for synapses in synapse_models %}
{% if synapses.connectivity != 'DENSE' %}
std::vector<size_t> sparseSynapseIndices{{synapses.name}};
{% endif %}
{% endfor %}
{% endmacro %}
