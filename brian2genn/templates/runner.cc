{% macro cpp_file() %}
//--------------------------------------------------------------------------
/*! \file runner.cu

\brief Main entry point for the running a model simulation. 
*/
//--------------------------------------------------------------------------


#include "runner.h"

{% for header in header_files %}
#include "{{header}}"
{% endfor %}



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
  
  name= OutDir+ "/"+ toString(argv[1]) + toString(".out.dat"); 
  FILE *osf= fopen(name.c_str(),"w");
  name.clear();
  name= OutDir+ "/"+ toString(argv[1]) + toString(".out.st"); 
  FILE *osfs= fopen(name.c_str(),"w");

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

  //------------------------------------------------------------------
  // output general parameters to output file and start the simulation
  fprintf(stderr, "# We are running with fixed time step %f \n", DT);

  t= 0.0;
  void *devPtr;
  int done= 0;
  //  eng.output_state(osf, which);  
  eng.output_spikes(osfs, which);
  eng.sum_spikes();
  cerr << "first run command" << endl;
  eng.run(DT, which);
  while (!done) 
  {
    if (which == GPU) {
      //      eng.getStateFromGPU();
      eng.getSpikesFromGPU();
    }
    eng.run(DT, which); // run next batch
    eng.output_spikes(osfs, which);
    eng.output_state(osf, which);
    eng.sum_spikes();
    cerr << t << " done ..." << endl;
    done= (t >= totalTime);
  }
  if (which == GPU) {
    //    eng.getStateFromGPU();
    eng.getSpikesFromGPU();
  }
  eng.output_spikes(osfs, which);
  eng.output_state(osf, which);
  eng.sum_spikes();
  timer.stopTimer();

  cerr << "output files are created under the current directory." << endl;
  {% for neuron_model in neuron_models %}
  fprintf(timef, "%d ", eng.sum{{neuron_model.name}});
  {% endfor %}
  fprintf(timef,"%f \n", timer.getElapsedTime());

  fclose(osf);
  fclose(osfs);

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


#define RAND(Y,X) Y = Y * 1103515245 +12345;X= (unsigned int)(Y >> 16) & 32767

// we will hard-code some stuff ... because at the end of the day that is 
// what we will do for the CUDA version

#define DBG_SIZE 10000

// and some global variables
double t= 0.0f;
unsigned int iT= 0;
CStopWatch timer;

//----------------------------------------------------------------------
// other stuff:

#include "engine.cc"

{% endmacro %}
