{% macro cpp_file() %}
//--------------------------------------------------------------------------
/*! \file runner.cu

\brief Main entry point for the running a model simulation. 
*/
//--------------------------------------------------------------------------


#include "runner.h"

//--------------------------------------------------------------------------
/*! \brief This function is the entry point for running the simulation of the MBody1 model network.
*/
//--------------------------------------------------------------------------


int main(int argc, char *argv[])
{
  if (argc != 3)
  {
    fprintf(stderr, "usage: runner <basename> <CPU=0, GPU=1> \n");
    return 1;
  }
  int which= atoi(argv[2]);
  string OutDir = toString(argv[1]) +"_output";
  string cmd= toString("mkdir ") +OutDir;
  system(cmd.c_str());
  string name;
  name= OutDir+ "/"+ toString(argv[1]) + toString(".time");
  FILE *timef= fopen(name.c_str(),"w");  

  timer.startTimer();
  fprintf(stderr, "# DT %f \n", DT);
  fprintf(stderr, "# TOTAL_TME %d \n", TOTAL_TME);
  
  name= OutDir+ "/"+ toString(argv[1]) + toString(".out.st"); 
  FILE *osf= fopen(name.c_str(),"w");
  //-----------------------------------------------------------------
  // build the neuronal circuitery
  engine eng;

  eng.init(which);         // this includes copying g's for the GPU version

  //------------------------------------------------------------------
  // output general parameters to output file and start the simulation

  fprintf(stderr, "# We are running with fixed time step %f \n", DT);

  t= 0.0;
  void *devPtr;
  int done= 0;
  eng.output_state(osf, which);  
  eng.run(DT, which);
  while (!done) 
  {
    if (which == GPU) eng.getSpikesFromGPU();
    eng.run(DT, which); // run next batch
    eng.output_state(osf, which);
    t+=DT;
    cerr << t << endl;
    done= (t >= TOTAL_TME);
  }
  if (which == GPU) eng.getSpikesFromGPU();
  eng.output_state(osf, which);

  cerr << "output files are created under the current directory." << endl;
  {% for neuron_model in neuron_models %}
  fprintf(timef, "%d ", eng.sum{{neuron_model.name}});
  {% endfor %}
  fprintf(timef,"%d \n", timer.getElapsedTime());

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
float t= 0.0f;
unsigned int iT= 0;
CStopWatch timer;

//----------------------------------------------------------------------
// other stuff:

#define TOTAL_TME 500000

#include "engine.cc"

{% endmacro %}
