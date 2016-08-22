{% macro cpp_file() %}
{% block maincode %}
{{vector_code|autoindent}}
{% endblock %}
{% endmacro %}

{% macro h_file() %}
{{support_code_lines|autoindent}}
{% endmacro %}

