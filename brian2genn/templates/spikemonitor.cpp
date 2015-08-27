{% extends 'common_group.cpp' %}


{% block extra_headers %}
{% set sourcename= eventspace_variable.owner.name %}
extern double t;
extern int which;
#include "sparseProjection.h"
#include "magicnetwork_model_CODE/definitions.h"
{% for varname, var in record_variables.items() %}
{% if varname != 't' %}
{% if varname == 'i' %}
extern unsigned int *glbSpkCnt{{sourcename}};
extern unsigned int *glbSpk{{sourcename}};
{% else %}
extern {{c_data_type(var.dtype)}} *{{var.name}}{{sourcename}};
{% endif %}
{% endif %}
{% endfor %}
{% endblock %}

{% block maincode %}
{% set sourcename= eventspace_variable.owner.name %}
	//// MAIN CODE ////////////
    {# USES_VARIABLES { N, _clock_t, count,
                        _source_start, _source_stop} #}
    {#  Get the name of the array that stores these events (i.e. the spikespace array - other cases not (yet?) supported) #}
    {% set _eventspace = 'spike_'+sourcename %}
    {% set _num_events = 'spikeCount_'+sourcename %}
	int32_t _num_events = {{_num_events}};

    if (which == 1) { // need to pull monitored data from GPU
	{% for varname, var in record_variables.items() %}
	{% if (varname != 't') and (varname != 'i') %}
	pull{{sourcename}}StateFromDevice();
	{% endif %}
	{% endfor %}
    }

    if (_num_events > 0)
    {
	unsigned int _true_events= 0;
	for(int _j=0; _j<_num_events; _j++)
	{
	    const int _idx = {{_eventspace}}[_j];
	    if ((_idx >= _source_start) && (_idx <= _source_stop)) {
		{% for varname, var in record_variables.items() %}
		{% if varname == 't' %}
		{{get_array_name(var, access_data=False)}}.push_back(t);
		{% else %}
		{% if varname == 'i' %}
		{{get_array_name(var, access_data=False)}}.push_back(_idx);
		{% else %}
		{{get_array_name(var, access_data=False)}}.push_back({{varname}}{{sourcename}}[glbSpkShift{{sourcename}}+_idx]);
		{% endif %}
		{% endif %}
		{% endfor %}
		{{count}}[_idx-_source_start]++;
		_true_events++;
	    }
	}
	{{N}}[0] += _true_events;
    }

{% endblock %}

{% block extra_functions_cpp %}
void _debugmsg_{{codeobj_name}}()
{
	using namespace brian;
	{# We need the pointers and constants here to get the access to N working #}
    %CONSTANTS%
    {{pointers_lines|autoindent}}
	std::cout << "Number of spikes: " << {{N}}[0] << endl;
}
{% endblock %}

{% block extra_functions_h %}
void _debugmsg_{{codeobj_name}}();
{% endblock %}

{% macro main_finalise() %}
_debugmsg_{{codeobj_name}}();
{% endmacro %}
