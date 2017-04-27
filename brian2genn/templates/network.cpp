{# Dummy file to allow the use of Brian2's object.cpp without changes #}
{% macro cpp_file() %}
{% endmacro %}

{% macro h_file() %}

#ifndef _BRIAN_NETWORK_H
#define _BRIAN_NETWORK_H
class Network
{
    public:
        static double _last_run_time;
        static double _last_run_completed_fraction;
};

#endif

{% endmacro %}