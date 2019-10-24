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

#include <ctime>
#include "magicnetwork_model_CODE/definitions.h"
#include "network.h"

double Network::_last_run_time = 0.0;
double Network::_last_run_completed_fraction = 0.0;

class engine
{
 public:
  NNmodel model;
  // end of data fields 

  engine();
  ~engine();
  void init(unsigned int); 
  void free_device_mem(); 
  void run(double, unsigned int); 
#ifndef CPU_ONLY
  void getStateFromGPU(); 
  void getSpikesFromGPU(); 
#endif
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
#include "network.h"

engine::engine()
{
  modelDefinition(model);
  allocateMem();
  initialize();
  Network::_last_run_time= 0.0;
  Network::_last_run_completed_fraction= 0.0;
}

//--------------------------------------------------------------------------
/*! \brief Method for initialising variables
 */
//--------------------------------------------------------------------------

void engine::init(unsigned int which)
{
#ifndef CPU_ONLY
  if (which == CPU) {
  }
  if (which == GPU) {
    copyStateToDevice();
  }
#endif
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

void engine::run(double duration, //!< Duration of time to run the model for 
		  unsigned int which //!< Flag determining whether to run on GPU or CPU only
		  )
{
  std::clock_t start, current; 
  const double t_start = t;
  unsigned int pno;
  unsigned int offset= 0;

  start = std::clock();
  int riT= (int) (duration/DT+1e-2);
  double elapsed_realtime;

  for (int i= 0; i < riT; i++) {
      // The StateMonitor and run_regularly operations are ordered by their "order" value
      {% for is_state_monitor, obj in run_reg_state_monitor_operations %}
      {% if is_state_monitor %}
      {% if obj.when == 'start' %}
      {% for var in obj.variables %}
      {% if obj.isSynaptic %}
      {% if obj.connectivity == 'DENSE' %}
      convert_dense_matrix_2_dynamic_arrays({{var}}{{obj.monitored}},
                                            {{obj.srcN}}, {{obj.trgN}},
                                            brian::_dynamic_array_{{obj.monitored}}__synaptic_pre,
                                            brian::_dynamic_array_{{obj.monitored}}__synaptic_post,
                                            brian::_dynamic_array_{{obj.monitored}}_{{var}});
      {% else %}
      convert_sparse_synapses_2_dynamic_arrays(C{{obj.monitored}},
                                               {{var}}{{obj.monitored}},
                                               {{obj.srcN}}, {{obj.trgN}},
                                               brian::_dynamic_array_{{obj.monitored}}__synaptic_pre,
                                               brian::_dynamic_array_{{obj.monitored}}__synaptic_post,
                                               brian::_dynamic_array_{{obj.monitored}}_{{var}},
                                               b2g::FULL_MONTY);
      {% endif %}
      {% else %}
      copy_genn_to_brian({{var}}{{obj.monitored}}, brian::_array_{{obj.monitored}}_{{var}}, {{obj.N}});
      {% endif %}
      {% endfor %}
      _run_{{obj.name}}_codeobject();
      {% endif %}
      {% else %}
      if (i % {{obj['step']}} == 0)
      {
          // Execute run_regularly operation: {{obj['name']}}
          {% for var in obj['read'] %}
          {% if var == 't' %}
          copy_genn_to_brian(&t, brian::_array_{{obj['owner'].clock.name}}_t, 1);
          {% elif var == 'dt' %}
          {# nothing to do #}
          {% else %}
          {% if obj['isSynaptic'] %}
          {% if obj['connectivity'] == 'DENSE' %}
          convert_dense_matrix_2_dynamic_arrays({{var}}{{obj['owner'].name}},
                                                {{obj['srcN']}}, {{obj['trgN']}},
                                                brian::_dynamic_array_{{obj['owner'].name}}__synaptic_pre,
                                                brian::_dynamic_array_{{obj['owner'].name}}__synaptic_post,
                                                brian::_dynamic_array_{{obj['owner'].name}}_{{var}});
          {% else %}
          convert_sparse_synapses_2_dynamic_arrays(C{{obj['owner'].name}}, {{var}}{{obj['owner'].name}},
                                                   {{obj['srcN']}}, {{obj['trgN']}},
                                                   brian::_dynamic_array_{{obj['owner'].name}}__synaptic_pre,
                                                   brian::_dynamic_array_{{obj['owner'].name}}__synaptic_post,
                                                   brian::_dynamic_array_{{obj['owner'].name}}_{{var}}, b2g::FULL_MONTY);
          {% endif %}
          {% else %}
           copy_genn_to_brian({{var}}{{obj['owner'].name}},
                              brian::_array_{{obj['owner'].name}}_{{var}},
                              {{obj['owner'].variables[var].size}});
          {% endif %}
          {% endif %}
          {% endfor %}

          _run_{{obj['codeobj'].name}}();

           {% for var in obj['write'] %}
           {% if obj['isSynaptic'] %}
           {% if obj['connectivity'] == 'DENSE' %}
           convert_dynamic_arrays_2_dense_matrix(brian::_dynamic_array_{{obj['owner'].name}}__synaptic_pre,
                                                 brian::_dynamic_array_{{obj['owner'].name}}__synaptic_post,
                                                 brian::_dynamic_array_{{obj['owner'].name}}_{{var}},
                                                 {{var}}{{obj['owner'].name}},
                                                 {{obj['srcN']}}, {{obj['trgN']}});
           {% else %}
           convert_dynamic_arrays_2_sparse_synapses(brian::_dynamic_array_{{obj['owner'].name}}__synaptic_pre,
                                                    brian::_dynamic_array_{{obj['owner'].name}}__synaptic_post,
                                                    brian::_dynamic_array_{{obj['owner'].name}}_{{var}},
                                                    {{var}}{{obj['owner'].name}},
                                                    {{obj['srcN']}}, {{obj['trgN']}},
                                                    _{{obj['owner'].name}}_bypre);
           {% endif %}
           {% else %}
           copy_brian_to_genn(brian::_array_{{obj['owner'].name}}_{{var}},
                              {{var}}{{obj['owner'].name}},
                              {{obj['owner'].variables[var].size}});
           {% endif %}
           {% endfor %}
      }
      {% endif %}
      {% endfor %}
#ifndef CPU_ONLY
      if (which == GPU) {
          {% for run_reg in run_regularly_operations %}
          {% for var in run_reg['write'] %}
          push{{run_reg['owner'].variables[var].owner.name}}StateToDevice();
          {% endfor %}
          {% endfor %}
          stepTimeGPU();
          // The stepTimeGPU function already updated everything for the next time step
          iT--;
          t = iT*DT;
          {% for spkGen in spikegenerator_models %}
          _run_{{spkGen.name}}_codeobject();
          push{{spkGen.name}}SpikesToDevice();
          {% endfor %}
          {% for spkMon in spike_monitor_models %}
          {% if (spkMon.notSpikeGeneratorGroup) %}
          pull{{spkMon.neuronGroup}}SpikesFromDevice();
          {% endif %}
          {% endfor %}
          {% for rateMon in rate_monitor_models %}
          {% if (rateMon.notSpikeGeneratorGroup) %}
          pull{{rateMon.neuronGroup}}SpikesFromDevice();
          {% endif %}
          {% endfor %}
          {% for sm in state_monitor_models %}
          pull{{sm.monitored}}StateFromDevice();
          {% endfor %}
          {% for run_reg in run_regularly_operations %}
            {% for var in run_reg['read'] %}
            {% if not var in ['t', 'dt'] %}
            pull{{run_reg['owner'].variables[var].owner.name}}StateFromDevice();
            {% endif %}
            {% endfor %}
          {% endfor %}
      }
#endif
      if (which == CPU) {
          stepTimeCPU();
          // The stepTimeGPU function already updated everything for the next time step
          iT--;
          t = iT*DT;
          {% for spkGen in spikegenerator_models %}
          _run_{{spkGen.name}}_codeobject();
          {% endfor %}
      }
      // report state 
      {% for sm in state_monitor_models %}
      {% if sm.when != 'start' %}
      {% for var in sm.variables %}
      {% if sm.isSynaptic %}
      {% if sm.connectivity == 'DENSE' %}
      convert_dense_matrix_2_dynamic_arrays({{var}}{{sm.monitored}}, {{sm.srcN}}, {{sm.trgN}},brian::_dynamic_array_{{sm.monitored}}__synaptic_pre, brian::_dynamic_array_{{sm.monitored}}__synaptic_post, brian::_dynamic_array_{{sm.monitored}}_{{var}});
      {% else %}
      convert_sparse_synapses_2_dynamic_arrays(C{{sm.monitored}}, {{var}}{{sm.monitored}}, {{sm.srcN}}, {{sm.trgN}}, brian::_dynamic_array_{{sm.monitored}}__synaptic_pre, brian::_dynamic_array_{{sm.monitored}}__synaptic_post, brian::_dynamic_array_{{sm.monitored}}_{{var}}, b2g::FULL_MONTY);
      {% endif %}
      {% else %}
      copy_genn_to_brian({{var}}{{sm.monitored}}, brian::_array_{{sm.monitored}}_{{var}}, {{sm.N}});
      {% endif %}
      {% endfor %}
      _run_{{sm.name}}_codeobject();
      {% endif %}
      {% endfor %}
      // report spikes
      {% for spkMon in spike_monitor_models %}
      _run_{{spkMon.name}}_codeobject();
      {% endfor %}
      {% for rateMon in rate_monitor_models %}
      _run_{{rateMon.name}}_codeobject();
      {% endfor %}
      // Bring the time step back to the value for the next loop iteration
      iT++;
      t = iT*DT;
      {% if maximum_run_time is not none %}
      current= std::clock();
      elapsed_realtime= (double) (current - start)/CLOCKS_PER_SEC;
      if (elapsed_realtime > {{maximum_run_time}}) {
        break;
      }
      {% endif %}
  }  
  {% if maximum_run_time is none %}
  current= std::clock();
  elapsed_realtime= (double) (current - start)/CLOCKS_PER_SEC;
  {% endif %}
  Network::_last_run_time = elapsed_realtime;
  if (duration > 0.0)
  {
      Network::_last_run_completed_fraction = (t-t_start)/duration;
  } else {
      Network::_last_run_completed_fraction = 1.0;
  }
}


#ifndef CPU_ONLY
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


#endif


#endif	

{% endmacro %}
