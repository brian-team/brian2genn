{# IS_OPENMP_COMPATIBLE #}
{% extends 'common_group.cpp' %}

{% block extra_headers %}
extern double t;
#include "sparseProjection.h"
#include "magicnetwork_model_CODE/definitions.h"
{% endblock%}

{% block maincode %}
	{# USES_VARIABLES { rate, t, _clock_t, _clock_dt, _spikespace,
	                    _num_source_neurons, _source_start, _source_stop } #}

        {% set sourcename= _spikespace.replace('_ptr_array_','').replace('__spikespace','') %}
        int _num_spikes = spikeCount_{{sourcename}};
	// For subgroups, we do not want to record all spikes
        // We cannot assume that spikes are ordered!

        unsigned int _nSpikes= 0;
        for(int _j=0; _j<_num_spikes; _j++)
        {
            const int _idx = spike_{{sourcename}}[_j];
 	    if ((_idx >= _source_start) && (_idx < _source_stop)) {
		_nSpikes++;
	    }
	}
	{{_dynamic_rate}}.push_back(1.0*_nSpikes/{{_clock_dt}}/_num_source_neurons);
	{{_dynamic_t}}.push_back(t);
{% endblock %}

