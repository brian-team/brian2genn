{% macro h_file() %}

#ifndef ENGINE_H
#define ENGINE_H

//--------------------------------------------------------------------------
/*! \file engine.h

\brief Header file containing the class definition for the engine to conveniently run a model in GeNN
*/
//--------------------------------------------------------------------------


#include "{{model_name}}.cc"

//--------------------------------------------------------------------------
/*! \brief This class contains the methods for running the model.
 */
//--------------------------------------------------------------------------

class engine
{
 public:
  NNmodel model;
  //------------------------------------------------------------------------
  // on the device:
  //------------------------------------------------------------------------
  {% for neuron_model in neuron_models %} 
  unsigned int sum{{neuron_model.name}};
  {% endfor %}
  // end of data fields 

  engine();
  ~engine();
  void init(unsigned int); 
  void free_device_mem(); 
  void run(float, unsigned int); 
  void output_state(FILE *, unsigned int); 
  void getSpikesFromGPU(); 
  void getSpikeNumbersFromGPU(); 
  void output_spikes(FILE *, unsigned int); 
  void sum_spikes(); 
};

#endif
{% endmacro %}


{% macro cpp_file() %}
#ifndef _MAP_CLASSOL_CC_
#define _MAP_CLASSOL_CC_


//--------------------------------------------------------------------------
/*! \file map_classol.cc
\brief Implementation of the engine class.
*/
//--------------------------------------------------------------------------

#include "engine.h"
#include "{{model_name}}_CODE/runner.cc"

engine::engine()
{
  modelDefinition(model);
  allocateMem();
  initialize();
  {% for neuron_model in neuron_models %}
  sum{{neuron_model.name}}= 0;
  {% endfor %}
}

//--------------------------------------------------------------------------
/*! \brief Method for initialising variables
 */
//--------------------------------------------------------------------------

void engine::init(unsigned int which)
{
  if (which == CPU) {
  }
  if (which == GPU) {
    copyGToDevice(); 
    copyStateToDevice();
  }
}

//--------------------------------------------------------------------------
//--------------------------------------------------------------------------

engine::~engine()
{
}


//--------------------------------------------------------------------------
/*! \brief Method for simulating the model for a given period of time
 */
//--------------------------------------------------------------------------

void engine::run(float runtime, //!< Duration of time to run the model for 
		  unsigned int which //!< Flag determining whether to run on GPU or CPU only
		  )
{
  unsigned int pno;
  unsigned int offset= 0;
  int riT= (int) (runtime/DT+1e-2);

  for (int i= 0; i < riT; i++) {
    if (which == GPU)
       stepTimeGPU(t);
    if (which == CPU)
       stepTimeCPU(t);
    t+= DT;
    iT++;
  }
}

//--------------------------------------------------------------------------
// output functions

//--------------------------------------------------------------------------
/*! \brief Method for copying from device and writing out to file of the entire state of the model
 */
//--------------------------------------------------------------------------

void engine::output_state(FILE *f, //!< File handle for a file to write the model state to 
			   unsigned int which //!< Flag determining whether using GPU or CPU only
			   )
{
  if (which == GPU) 
    copyStateFromDevice();

  fprintf(f, "%f ", t);
  {% for neuron_model in neuron_models %}
  for (int i= 0; i < model.neuronN[{{loop.index-1}}]; i++) {
    fprintf(f, "%f ", V{{neuron_model.name}}[i]);
  }
  {% endfor %}
  fprintf(f,"\n");
}

//--------------------------------------------------------------------------
/*! \brief Method for copying all spikes of the last time step from the GPU
 
  This is a simple wrapper for the convenience function copySpikesFromDevice() which is provided by GeNN.
*/
//--------------------------------------------------------------------------

void engine::getSpikesFromGPU()
{
  copySpikesFromDevice();
}

//--------------------------------------------------------------------------
/*! \brief Method for copying the number of spikes in all neuron populations that have occurred during the last time step
 
This method is a simple wrapper for the convenience function copySpikeNFromDevice() provided by GeNN.
*/
//--------------------------------------------------------------------------

void engine::getSpikeNumbersFromGPU() 
{
  copySpikeNFromDevice();
}

//--------------------------------------------------------------------------
/*! \brief Method for writing the spikes occurred in the last time step to a file
 */
//--------------------------------------------------------------------------

void engine::output_spikes(FILE *f, //!< File handle for a file to write spike times to
			    unsigned int which //!< Flag determining whether using GPU or CPU only
			    )
{
  {% for neuron_model in neuron_models %}
  for (int i= 0; i < glbscnt{{neuron_model.name}}; i++) {
    fprintf(f, "%f %d\n", t, glbSpk{{neuron_model.name}}[i]);
  }
  {% endfor %}
}

//--------------------------------------------------------------------------
/*! \brief Method for summing up spike numbers
 */
//--------------------------------------------------------------------------

void engine::sum_spikes()
{
  {% for neuron_model in neuron_models %}
  sum{{neuron_model.name}}+= glbscnt{{neuron_model.name}};
  {% endfor %}
}

#endif	

{% endmacro %}
