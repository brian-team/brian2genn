{% macro cpp_file() %}
//--------------------------------------------------------------------------
/*! \file runner.cu

\brief Main entry point for the running a model simulation. 
*/
//--------------------------------------------------------------------------

#include "runner.h"
#include "{{model_name}}.cc"
#include "{{model_name}}_CODE/runner.cc"

{% for header in header_files %}
#include "{{header}}"
{% endfor %}

#include "engine.cc"


//--------------------------------------------------------------------------
/*! \brief This function is the entry point for running the simulation of the MBody1 model network.
*/
//--------------------------------------------------------------------------


int main(int argc, char *argv[])
{
  if (argc != 4)
  {
    fprintf(stderr, "usage: runner <basename> <time (s)> <CPU=0, GPU=1> \n");
    return 1;
  }
  double totalTime= atof(argv[2]);
  int which= atoi(argv[3]);
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

  {
	  using namespace brian;
	  {{ main_lines | autoindent }}
  }

  // translate to GeNN synaptic arrays
  {% for synapses in synapse_models %}
  {% for var in synapses.variables %}
  convert_dynamic_arrays_2_dense_matrix(brian::_dynamic_array_{{synapses.name}}__synaptic_pre, brian::_dynamic_array_{{synapses.name}}__synaptic_post, brian::_dynamic_array_{{synapses.name}}_{{var}}, {{var}}{{synapses.name}}, {{synapses.srcN}}, {{synapses.trgN}});
  {% endfor %}
  create_hidden_weightmatrix(brian::_dynamic_array_{{synapses.name}}__synaptic_pre, brian::_dynamic_array_{{synapses.name}}__synaptic_post, _hidden_weightmatrix{{synapses.name}},{{synapses.srcN}}, {{synapses.trgN}});

  {% for var in synapses.postsyn_variables %}
  convert_dynamic_arrays_2_dense_matrix(brian::_dynamic_array_{{synapses.name}}__synaptic_pre, brian::_dynamic_array_{{synapses.name}}__synaptic_post, brian::_dynamic_array_{{synapses.name}}_{{var}}, {{var}}{{synapses.name}}, {{synapses.srcN}}, {{synapses.trgN}});
  {% endfor %}
  {% endfor %}

  // copy variable arrays
  {% for neuron in neuron_models %} 
  {% for var in neuron.variables %}
  copy_brian_to_genn(brian::_array_{{neuron.name}}_{{var}}, {{var}}{{neuron.name}}, {{neuron.N}});
  {% endfor %}
  {% endfor %}
  

  //-----------------------------------------------------------------
  
  eng.init(which);         // this includes copying g's for the GPU version
  copyStateToDevice();

  //------------------------------------------------------------------
  // output general parameters to output file and start the simulation
  fprintf(stderr, "# We are running with fixed time step %f \n", DT);

  t= 0.0;
  void *devPtr;
  int done= 0;
  cerr << "first run command" << endl;
  while (!done) 
  {
    eng.run(DT, which); // run next batch
    done= (t >= totalTime);
  }
  timer.stopTimer();
  cerr << t << " done ..." << endl;
  fprintf(timef,"%f \n", timer.getElapsedTime());

// translate to GeNN synaptic arrays
  {% for synapses in synapse_models %}
  {% for var in synapses.variables %}
  convert_dense_matrix_2_dynamic_arrays({{var}}{{synapses.name}}, {{synapses.srcN}}, {{synapses.trgN}},brian::_dynamic_array_{{synapses.name}}__synaptic_pre, brian::_dynamic_array_{{synapses.name}}__synaptic_post, brian::_dynamic_array_{{synapses.name}}_{{var}});
  {% endfor %}
  {% for var in synapses.postsyn_variables %}
  convert_dense_matrix_2_dynamic_arrays({{var}}{{synapses.name}}, {{synapses.srcN}}, {{synapses.trgN}}, brian::_dynamic_array_{{synapses.name}}__synaptic_pre, brian::_dynamic_array_{{synapses.name}}__synaptic_post, brian::_dynamic_array_{{synapses.name}}_{{var}});
  {% endfor %}
  {% endfor %}

  // copy variable arrays
  {% for neuron in neuron_models %} 
  {% for var in neuron.variables %}
  copy_genn_to_brian({{var}}{{neuron.name}}, brian::_array_{{neuron.name}}_{{var}}, {{neuron.N}});
  {% endfor %}
  {% endfor %}
  
  _write_arrays();
  _dealloc_arrays();
  return 0;
}

{% endmacro %}

{% macro h_file() %}
//--------------------------------------------------------------------------
/*! \file runner.h

\brief Header file containing global variables and macros used in running the model.
*/
//--------------------------------------------------------------------------

using namespace std;
#include <cassert>

#include "hr_time.cpp"
#include "utils.h" // for CHECK_CUDA_ERRORS

#include <cuda_runtime.h>

#ifndef RAND
#define RAND(Y,X) Y = Y * 1103515245 +12345;X= (unsigned int)(Y >> 16) & 32767
#endif

// we will hard-code some stuff ... because at the end of the day that is 
// what we will do for the CUDA version

#define DBG_SIZE 10000

// and some global variables
double t= 0.0;
unsigned int iT= 0;
CStopWatch timer;

//----------------------------------------------------------------------
// other stuff:


{% endmacro %}
