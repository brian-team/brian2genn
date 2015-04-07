{% extends 'common_group.cpp' %}

{% block extra_headers %}
#include "magicnetwork_model_CODE/definitions.h"

extern unsigned int *{{_spikespace.replace('_ptr_array_','glbSpkCnt').replace('__spikespace','')}};
extern unsigned int *{{_spikespace.replace('_ptr_array_','glbSpk').replace('__spikespace','')}};
extern double t;
{% endblock %}

{% block maincode %}
	{# USES_VARIABLES {_spikespace, N, t, dt, neuron_index, spike_time } #}

    // TODO: We don't deal with more than one spike per neuron yet
    long _cpp_numspikes = 0;
    // Note that std:upper_bound returns a pointer but we want indices
    const unsigned int _start_idx = std::upper_bound({{spike_time}},
                                                     {{spike_time}} + _numspike_time,
                                                     t-dt) - {{spike_time}};
    const unsigned int _stop_idx = std::upper_bound({{spike_time}},
                                                    {{spike_time}} + _numspike_time,
                                                    t) - {{spike_time}};

	for(int _idx=_start_idx; _idx<_stop_idx; _idx++)
	{
        {{_spikespace.replace('_ptr_array_','spike_').replace('__spikespace','')}}[_cpp_numspikes++] = {{neuron_index}}[_idx];
	}
	{{_spikespace.replace('_ptr_array_','spikeCount_').replace('__spikespace','')}} = _cpp_numspikes;
{% endblock %}
