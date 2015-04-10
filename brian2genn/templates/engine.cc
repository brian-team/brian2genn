{% macro h_file() %}

#ifndef ENGINE_H
#define ENGINE_H

//--------------------------------------------------------------------------
/*! \file engine.h

\brief Header file containing the class definition for the engine to conveniently run a model in GeNN
*/
//--------------------------------------------------------------------------

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
  void run(double, unsigned int); 
  void output_state(FILE *, unsigned int); 
  void getStateFromGPU(); 
  void getSpikesFromGPU(); 
  void getSpikeNumbersFromGPU(); 
  void output_spikes(FILE *, unsigned int); 
  void sum_spikes(); 
};

#endif
{% endmacro %}


{% macro cpp_file() %}
#ifndef _ENGINE_CC_
#define _ENGINE_CC_


//--------------------------------------------------------------------------
/*! \file engine.cc
\brief Implementation of the engine class.
*/
//--------------------------------------------------------------------------

#include "engine.h"

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

void engine::run(double runtime, //!< Duration of time to run the model for 
		  unsigned int which //!< Flag determining whether to run on GPU or CPU only
		  )
{
  unsigned int pno;
  unsigned int offset= 0;
  int riT= (int) (runtime/DT+1e-2);

  for (int i= 0; i < riT; i++) {
      if (which == GPU) {
	  stepTimeGPU(t);
	  {% for spkGen in spikegenerator_models %}
	  _run_{{spkGen.name}}_codeobject();
	  push{{spkGen.name}}SpikesToDevice();
	  {% endfor %}
	  {% for spkMon in spike_monitor_models %}
	  {% if (spkMon.notSpikeGeneratorGroup) %}
	  pull{{spkMon.neuronGroup}}SpikesFromDevice();
	  {% endif %}
	  _run_{{spkMon.name}}_codeobject();
	  {% endfor %}
	  {% for stateMon in state_monitor_models %}
	  pull{{stateMon.neuronGroup}}StateFromDevice();
	  _run_{{stateMon.name}}_codeobject();
	  {% endfor %}
      }
      if (which == CPU) {
	  {% for spkGen in spikegenerator_models %}
	  _run_{{spkGen.name}}_codeobject();
	  {% endfor %}
	  stepTimeCPU(t);
	  {% for spkMon in spike_monitor_models %}
	  _run_{{spkMon.name}}_codeobject();
	  {% endfor %}
	  {% for stateMon in state_monitor_models %}
	  _run_{{stateMon.name}}_codeobject();
	  {% endfor %}
      }
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
      {% for var in neuron_model.variables %}
      fprintf(f, "%f ", (float) {{var}}{{neuron_model.name}}[i]);
      {% endfor %}
  }
  {% endfor %}

  {% for synapse_model in synapse_models %}
  for (int i= 0; i < model.neuronN[model.synapseSource[{{loop.index-1}}]]*model.neuronN[model.synapseTarget[{{loop.index-1}}]]; i++) {
      {% for var in synapse_model.variables %}
      fprintf(f, "%f ", (float) {{var}}{{synapse_model.name}}[i]);
      {% endfor %}
      {% for var in synapse_model.postsyn_variables %}
      fprintf(f, "%f ", (float) {{var}}{{synapse_model.name}}[i]);
      {% endfor %}
      {% for var in synapse_model.synapseDynamics_variables %}
      fprintf(f, "%f ", (float) {{var}}{{synapse_model.name}}[i]);
      {% endfor %}
  }
  {% endfor %}
  
  fprintf(f,"\n");
}

//--------------------------------------------------------------------------
/*! \brief Method for copying all variables of the last time step from the GPU
 
  This is a simple wrapper for the convenience function copyStateFromDevice() which is provided by GeNN.
*/
//--------------------------------------------------------------------------

void engine::getStateFromGPU()
{
  copyStateFromDevice();
}

//--------------------------------------------------------------------------
/*! \brief Method for copying all spikes of the last time step from the GPU
 
  This is a simple wrapper for the convenience function copySpikesFromDevice() which is provided by GeNN.
*/
//--------------------------------------------------------------------------

void engine::getSpikesFromGPU()
{
  copySpikeNFromDevice();
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
  for (int i= 0; i < glbSpkCnt{{neuron_model.name}}[0]; i++) {
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
  sum{{neuron_model.name}}+= glbSpkCnt{{neuron_model.name}}[0];
  {% endfor %}
}

#endif	

{% endmacro %}
