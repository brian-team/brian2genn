{% extends 'common_group.cpp' %}


{% block extra_headers %}
{% set sourcename= eventspace_variable.owner.name %}
#include "magicnetwork_model_CODE/definitions.h"
{% endblock %}

{% block maincode %}
{% set sourcename= eventspace_variable.owner.name %}
	//// MAIN CODE ////////////
    {# USES_VARIABLES { N, _clock_t, count,
                        _source_start, _source_stop} #}
    {# WRITES_TO_READ_ONLY_VARIABLES { N, count } #}
    {#  Get the name of the array that stores these events (i.e. the spikespace array - other cases not (yet?) supported) #}
    {% set _eventspace = 'spike_'+sourcename %}
    {% set _num_events = 'spikeCount_'+sourcename %}
	int32_t _num_events = {{_num_events}};

	{% for varname, var in record_variables.items() %}
	{% if (varname != 't') and (varname != 'i') %}
	pull{{sourcename}}CurrentSpikesFromDevice();
	{% endif %}
	{% endfor %}


    if (_num_events > 0)
    {
	unsigned int _true_events= 0;
	for(int _j=0; _j<_num_events; _j++)
	{
	    const int _idx = {{_eventspace}}[_j];
	    if ((_idx >= _source_start) && (_idx < _source_stop)) {
		{% for varname, var in record_variables.items() %}
		{% if varname == 't' %}
		{{get_array_name(var, access_data=False)}}.push_back(t);
		{% else %}
		{% if varname == 'i' %}
		{{get_array_name(var, access_data=False)}}.push_back(_idx - _source_start);
		{% else %}
		{{get_array_name(var, access_data=False)}}.push_back({{varname}}{{sourcename}}[glbSpkShift{{sourcename}}+_idx]);
		{% endif %}
		{% endif %}
		{% endfor %}
		{{count}}[_idx-_source_start]++;
		_true_events++;
	    }
	}
	{{N}} += _true_events;
    }

{% endblock %}
