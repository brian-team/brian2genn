{% macro cpp_file() %}
//--------------------------------------------------------------------------
/*! \file main.cu

\brief Main entry point for the running a model simulation. 
*/
//--------------------------------------------------------------------------

#include "main.h"
#include "{{model_name}}.cpp"
#include "{{model_name}}_CODE/definitions.h"

{% for header in header_files %}
#include "{{header}}"
{% endfor %}

#include "engine.cpp"


//--------------------------------------------------------------------------
/*! \brief This function is the entry point for running the simulation of the MBody1 model network.
*/
//--------------------------------------------------------------------------
int which;

int main(int argc, char *argv[])
{
  if (argc != 4)
  {
    fprintf(stderr, "usage: main <basename> <time (s)> <CPU=0, GPU=1> \n");
    return 1;
  }
  double totalTime= atof(argv[2]);
  which= atoi(argv[3]);
  string OutDir = toString(argv[1]) +"_output";
  string cmd= toString("mkdir ") +OutDir;
  system(cmd.c_str());
  string name;
  name= OutDir+ "/"+ toString(argv[1]) + toString(".time");
  FILE *timef= fopen(name.c_str(),"a");  

  timer.startTimer();
  fprintf(stderr, "# DT %f \n", DT);
  fprintf(stderr, "# totalTime %f \n", totalTime);
  
  //-----------------------------------------------------------------
  // build the neuronal circuitery
  engine eng;

  //-----------------------------------------------------------------
  // load variables and parameters and translate them from Brian to Genn
  _init_arrays();
  _load_arrays();
  rk_randomseed(brian::_mersenne_twister_states[0]);
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
  allocate{{synapses.name}}(brian::_dynamic_array_{{synapses.name}}__synaptic_pre.size());
   {% set _first_var = true %}
   {% for var in synapses.variables %}
   {% if synapses.variablescope[var] == 'brian' %}
      {% if _first_var %}
      {% set _mode = 'b2g::FULL_MONTY' %}
      {% set _first_var = false %}
      {% else %}
      {% set _mode = 'b2g::COPY_ONLY' %}
      {% endif %}
      convert_dynamic_arrays_2_sparse_synapses(brian::_dynamic_array_{{synapses.name}}__synaptic_pre, brian::_dynamic_array_{{synapses.name}}__synaptic_post, brian::_dynamic_array_{{synapses.name}}_{{var}}, C{{synapses.name}}, {{var}}{{synapses.name}}, {{synapses.srcN}}, {{synapses.trgN}}, {{_mode}});
  {% endif %}
  {% endfor %} {# all synapse variables #}
  {% endif %} {# dense/sparse #}
  {% for var in synapses.shared_variables %}
  copy_brian_to_genn(brian::_array_{{synapses.name}}_{{var}}, &{{var}}{{synapses.name}}, 1);
  {% endfor %} {# shared variables #}
  {% endfor %} {# all synapse_models #}
  initmagicnetwork_model();

  // copy variable arrays
  {% for neuron in neuron_models %} 
  {% for var in neuron.variables %}
  {% if neuron.variablescope[var] == 'brian' %}
  copy_brian_to_genn(brian::_array_{{neuron.name}}_{{var}}, {{var}}{{neuron.name}}, {{neuron.N}});
  {% endif %}
  {% endfor %}
  {% endfor %}

  // copy scalar variables
  {% for neuron in neuron_models %}
  {% for var in neuron.shared_variables %}
  copy_brian_to_genn(brian::_array_{{neuron.name}}_{{var}}, &{{var}}{{neuron.name}}, 1);
  {% endfor %}
  {% endfor %}
  
  // initialise random seeds (if any are used)
  {% for neuron in neuron_models %} 
  {% if '_seed' in neuron.variables %}
  for (int i= 0; i < {{neuron.N}}; i++) {
      _seed{{neuron.name}}[i]= (uint64_t) (rand()*MYRAND_MAX);
  }
  {% endif %}
  {% endfor %}
  {% for synapses in synapse_models %}
  {% if '_seed' in synapses.variables %}
  for (int i= 0; i < C{{synapses.name}}.connN; i++) {
      _seed{{synapses.name}}[i]= (uint64_t) (rand()*MYRAND_MAX);
  }
  {% endif %}
  {% endfor %}

  //-----------------------------------------------------------------
  
  eng.init(which);         // this includes copying g's for the GPU version
#ifndef CPU_ONLY
  copyStateToDevice();
#endif

  //------------------------------------------------------------------
  // output general parameters to output file and start the simulation
  fprintf(stderr, "# We are running with fixed time step %f \n", DT);

  t= -DT;
  void *devPtr;
  eng.run(totalTime, which); // run for the full duration
  timer.stopTimer();
  cerr << t << " done ..." << endl;
  fprintf(timef,"%f \n", timer.getElapsedTime());

  // get the final results from the GPU 
#ifndef CPU_ONLY
  if (which == GPU) {
    eng.getStateFromGPU();
    eng.getSpikesFromGPU();
  }
#endif
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
      convert_sparse_synapses_2_dynamic_arrays(C{{synapses.name}}, {{var}}{{synapses.name}}, {{synapses.srcN}}, {{synapses.trgN}}, brian::_dynamic_array_{{synapses.name}}__synaptic_pre, brian::_dynamic_array_{{synapses.name}}__synaptic_post, brian::_dynamic_array_{{synapses.name}}_{{var}}, {{_mode}});
  {% endif %}
  {% endfor %} {# all synapse variables #}
  {% endif %} {# dense/sparse #}
  {% for var in synapses.shared_variables %}
  copy_genn_to_brian(&{{var}}{{synapses.name}}, brian::_array_{{synapses.name}}_{{var}}, 1);
  {% endfor %} {# shared variables #}
  {% endfor %} {# all synapse_models #}

  // copy variable arrays
  {% for neuron in neuron_models %} 
  {% for var in neuron.variables %}
  {% if neuron.variablescope[var] == 'brian' %}
  copy_genn_to_brian({{var}}{{neuron.name}}, brian::_array_{{neuron.name}}_{{var}}, {{neuron.N}});
  {% endif %}
  {% endfor %}
  {% endfor %}

  // copy scalar variables
  {% for neuron in neuron_models %}
  {% for var in neuron.shared_variables %}
  copy_genn_to_brian(&{{var}}{{neuron.name}}, brian::_array_{{neuron.name}}_{{var}}, 1);
  {% endfor %}
  {% endfor %}

  _write_arrays();
  _dealloc_arrays();
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
#include "hr_time.h"

#include "utils.h" // for CHECK_CUDA_ERRORS
#include "stringUtils.h"

#ifndef CPU_ONLY
#include <cuda_runtime.h>
#else
#define __host__
#define __device__
#endif


#ifndef RAND
#define RAND(Y,X) Y = Y * 1103515245 +12345;X= (unsigned int)(Y >> 16) & 32767
#endif

// we will hard-code some stuff ... because at the end of the day that is 
// what we will do for the CUDA version

#define DBG_SIZE 10000

// and some global variables
CStopWatch timer;

//----------------------------------------------------------------------
// other stuff:


{% endmacro %}
