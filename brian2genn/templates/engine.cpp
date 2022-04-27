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
  // end of data fields

  engine();
  ~engine();
  void free_device_mem();
  void run(double);
  void getStateFromGPU();
  void getSpikesFromGPU();
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
  allocateMem();
  initialize();
  Network::_last_run_time= 0.0;
  Network::_last_run_completed_fraction= 0.0;
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

void engine::run(double duration)  //!< Duration of time to run the model for
{
  std::clock_t start, current;
  const double t_start = t;

  start = std::clock();
  int riT= (int) (duration/DT+1e-2);
  double elapsed_realtime;

  for (int i= 0; i < riT; i++) {
    // The StateMonitor and run_regularly operations are ordered by their "order" value
        {% for is_state_monitor, obj in run_reg_state_monitor_operations %}
    if (i % {{obj['step']}} == 0)
    {
          {% if is_state_monitor %}
      // Execute state monitor operation: {{obj['name']}}
            {% if obj.when == 'start' %}
              {% for var in obj.variables %}
                {# No need to convert/copy for variables only changed on the host #}
                {% if var + obj.monitored in vars_to_pull_for_start %}
                  {% if obj.isSynaptic %}
                    {% if obj.connectivity == 'DENSE' %}
        convert_dense_matrix_2_dynamic_arrays({{var}}{{obj.monitored}},
                                              {{obj.srcN}}, {{obj.trgN}},
                                              brian::_dynamic_array_{{obj.monitored}}__synaptic_pre,
                                              brian::_dynamic_array_{{obj.monitored}}__synaptic_post,
                                              brian::_dynamic_array_{{obj.monitored}}_{{var}});
                    {% else %}
        convert_sparse_synapses_2_dynamic_arrays(rowLength{{obj.monitored}},
                                                ind{{obj.monitored}},
                                                maxRowLength{{obj.monitored}},
                                                {{var}}{{obj.monitored}},
                                                {{obj.srcN}}, {{obj.trgN}},
                                                brian::_dynamic_array_{{obj.monitored}}__synaptic_pre,
                                                brian::_dynamic_array_{{obj.monitored}}__synaptic_post,
                                                brian::_dynamic_array_{{obj.monitored}}_{{var}},
                                                b2g::FULL_MONTY);
                    {% endif %}
                  {% else %}
                    {% if obj.src.variables[var].scalar %}
        *brian::_array_{{obj.monitored}}_{{var}} = {{var}}{{obj.monitored}};
                    {% else %}
        std::copy_n({{var}}{{obj.monitored}}, {{obj.N}}, brian::_array_{{obj.monitored}}_{{var}});
                    {% endif %}
                  {% endif %}
                {% endif %}
              {% endfor %}
      _run_{{obj.codeobject_name}}();
            {% endif %}
          {% else %}
      // Execute run_regularly operation: {{obj['name']}}
            {% for var in obj['read'] %}
              {% if var == 't' %}
      std::copy_n(&t, 1, brian::_array_{{obj['owner'].clock.name}}_t);
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
      convert_sparse_synapses_2_dynamic_arrays(rowLength{{obj['owner'].name}},
                                               ind{{obj['owner'].name}},
                                               maxRowLength{{obj['owner'].name}},
                                               {{var}}{{obj['owner'].name}},
                                               {{obj['srcN']}}, {{obj['trgN']}},
                                               brian::_dynamic_array_{{obj['owner'].name}}__synaptic_pre,
                                               brian::_dynamic_array_{{obj['owner'].name}}__synaptic_post,
                                               brian::_dynamic_array_{{obj['owner'].name}}_{{var}}, b2g::FULL_MONTY);
                  {% endif %}
                {% else %}
                  {% if obj['owner'].variables[var].scalar %}
      *brian::_array_{{obj['owner'].name}}_{{var}} = {{var}}{{obj['owner'].name}};
                  {% else %}
      std::copy_n({{var}}{{obj['owner'].name}}, {{obj['owner'].variables[var].size}},
      brian::_array_{{obj['owner'].name}}_{{var}});
                  {% endif %}
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
      convert_dynamic_arrays_2_sparse_synapses(brian::_dynamic_array_{{obj['owner'].name}}_{{var}},
                                               sparseSynapseIndices{{obj['owner'].name}},
                                               {{var}}{{obj['owner'].name}},
                                               {{obj['srcN']}}, {{obj['trgN']}});
                {% endif %}
              {% else %}
                {% if obj['owner'].variables[var].scalar %}
      {{var}}{{obj['owner'].name}} = *brian::_array_{{obj['owner'].name}}_{{var}};
                {% else %}
      std::copy_n(brian::_array_{{obj['owner'].name}}_{{var}}, {{obj['owner'].variables[var].size}}, {{var}}{{obj['owner'].name}});
                {% endif %}
              {% endif %}
            {% endfor %}
          {% endif %}
    }
        {% endfor %}
        {% set states_pushed = [] %}
        {% for run_reg in run_regularly_operations %}
    if (i % {{run_reg['step']}} == 0)  // only push state if we executed the operation
    {
          {% for var in run_reg['write'] %}
            {# Don't push variables that are not used on the device #}
            {% if var in groupDict[run_reg['owner'].name].variables %}
              {% if not run_reg['owner'].variables[var] in states_pushed %}
                {% set var_owner = run_reg['owner'].variables[var].owner %}
                {% if var_owner.__class__.__name__ == 'Synapses' %}
                  {% set push_name = var + var_owner.name%}
                {% else %}
                  {% set push_name = 'Current' + var + var_owner.name %}
                {% endif %}
                push{{push_name}}ToDevice();
                {% if states_pushed.append(run_reg['owner'].variables[var]) %}{% endif %}
              {% endif %}
            {% endif %}
          {% endfor %}
    }
        {% endfor %}
    stepTime();
    // The stepTimeGPU function already updated everything for the next time step
    iT--;
    t = iT*DT;
        {% for spkGen in spikegenerator_models %}
    _run_{{spkGen.codeobject_name}}();
    push{{spkGen.name}}SpikesToDevice();
        {% endfor %}
        {% set spikes_pulled = [] %}
        {% for spkMon in spike_monitor_models %}
          {% if (spkMon.notSpikeGeneratorGroup) %}
            {% if not spkMon.neuronGroup in spikes_pulled %}
    pull{{spkMon.neuronGroup}}CurrentSpikesFromDevice();
              {% if spikes_pulled.append(spkMon.neuronGroup) %}
              {% endif %}
            {% endif %}
          {% endif %}
        {% endfor %}
        {% for rateMon in rate_monitor_models %}
          {% if (rateMon.notSpikeGeneratorGroup) %}
            {% if not rateMon.neuronGroup in spikes_pulled %}
    pull{{rateMon.neuronGroup}}CurrentSpikesFromDevice();
              {% if spikes_pulled.append(rateMon.neuronGroup) %}
              {% endif %}
            {% endif %}
          {% endif %}
        {% endfor %}
        {% for key, steps in vars_to_pull_for_start.items() %}
          {% if steps[0] == 1 %}
    pull{{key}}FromDevice();
          {% else %}
    if (
            {%- for step in steps %}
              {% if loop.index > 1 %} || {% endif -%}
      ((i+1) % {{step}} == 0)
            {%- endfor -%}
    ) {
      pull{{key}}FromDevice();
    }
          {% endif %}
        {% endfor %}
        {% for key, steps in vars_to_pull_for_end.items() %}
          {% if steps[0] == 1 %}
    pull{{key}}FromDevice();
          {% else %}
    if (
            {%- for step in steps %}
              {% if loop.index > 1 %} || {% endif -%}
      ((i+1) % {{step}} == 0)
            {%- endfor -%}
    ) {
      pull{{key}}FromDevice();
    }
          {% endif %}
        {% endfor %}
    // report state
        {% for sm in state_monitor_models %}
          {% if sm.when != 'start' %}
    if (i % {{sm['step']}} == 0)
    {
      // Execute state monitor operation: {{sm['name']}}
            {% for var in sm.variables %}
              {# No need to convert/copy for variables only changed on the host #}
              {% if var + sm.monitored in vars_to_pull_for_end %}
                {% if sm.isSynaptic %}
                  {% if sm.connectivity == 'DENSE' %}
        convert_dense_matrix_2_dynamic_arrays({{var}}{{sm.monitored}},
                                              {{sm.srcN}}, {{sm.trgN}},
                                              brian::_dynamic_array_{{sm.monitored}}__synaptic_pre,
                                              brian::_dynamic_array_{{sm.monitored}}__synaptic_post,
                                              brian::_dynamic_array_{{sm.monitored}}_{{var}});
                  {% else %}
        convert_sparse_synapses_2_dynamic_arrays(rowLength{{sm.monitored}},
                                                ind{{sm.monitored}},
                                                maxRowLength{{sm.monitored}},
                                                {{var}}{{sm.monitored}},
                                                {{sm.srcN}}, {{sm.trgN}},
                                                brian::_dynamic_array_{{sm.monitored}}__synaptic_pre,
                                                brian::_dynamic_array_{{sm.monitored}}__synaptic_post,
                                                brian::_dynamic_array_{{sm.monitored}}_{{var}},
                                                b2g::FULL_MONTY);
                  {% endif %}
                {% else %}
                  {% if sm.src.variables[var].scalar %}
        *brian::_array_{{sm.monitored}}_{{var}} = {{var}}{{sm.monitored}};
                  {% else %}
        std::copy_n({{var}}{{sm.monitored}}, {{sm.N}}, brian::_array_{{sm.monitored}}_{{var}});
                  {% endif %}
                {% endif %}
              {% endif %}
            {% endfor %}
      _run_{{sm.codeobject_name}}();
    }
          {% endif %}
        {% endfor %}
    // report spikes
        {% for spkMon in spike_monitor_models %}
    _run_{{spkMon.codeobject_name}}();
        {% endfor %}
        {% for rateMon in rate_monitor_models %}
    _run_{{rateMon.codeobject_name}}();
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
  copyCurrentSpikesFromDevice();
}



#endif

{% endmacro %}
