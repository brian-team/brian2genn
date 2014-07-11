{% macro cpp_file() %}
{% for line in code_lines %}
{{line}}
{% endfor %}
{% endmacro %}

{% macro h_file() %}
{% endmacro %}
