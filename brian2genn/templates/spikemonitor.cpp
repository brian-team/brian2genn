{% extends 'common_group.cpp' %}

{% block extra_headers %}
#include "magicnetwork_model_CODE/definitions.h"

extern unsigned int *{{_spikespace.replace('_ptr_array_','glbSpkCnt').replace('__spikespace','')}};
extern unsigned int *{{_spikespace.replace('_ptr_array_','glbSpk').replace('__spikespace','')}};
extern double t;
{% endblock %}

{% block maincode %}
	//// MAIN CODE ////////////
    {# USES_VARIABLES { t, i, _clock_t, _spikespace, count,
                        _source_start, _source_stop} #}
	int _num_spikes = {{_spikespace.replace('_ptr_array_','spikeCount_').replace('__spikespace','')}};
	for(int _j=0; _j<_num_spikes; _j++)
	{
            const int _idx = {{_spikespace.replace('_ptr_array_','spike_').replace('__spikespace','')}}[_j];
	    if ((_idx >= _source_start) && (_idx <= _source_stop))
	    {{_dynamic_i}}.push_back(_idx-_source_start);
	    {{_dynamic_t}}.push_back(t);
	    {{count}}[_idx-_source_start]++;
        }
{% endblock %}

{% block extra_functions_cpp %}
void _debugmsg_{{codeobj_name}}()
{
	using namespace brian;
	std::cout << "Number of spikes: " << {{_dynamic_i}}.size() << endl;
}
{% endblock %}

{% block extra_functions_h %}
void _debugmsg_{{codeobj_name}}();
{% endblock %}

{% macro main_finalise() %}
_debugmsg_{{codeobj_name}}();
{% endmacro %}
