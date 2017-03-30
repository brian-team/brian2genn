{# ALLOWS_SCALAR_WRITE #}
{% extends 'common_group.cpp' %}
{% block maincode %}
int _vectorisation_idx = -1;
{{scalar_code['None']|autoindent}}
{% endblock %}
