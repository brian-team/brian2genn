{% macro stateupdate_code() %}
{{(scalar_code['stateupdate'] + vector_code['stateupdate'])|autoindent}}
{% endmacro %}

{% macro reset_code() %}
{{(scalar_code['reset'] + vector_code['reset'])|autoindent}}
{% endmacro %}

{% macro h_file() %}
{{support_code_lines|autoindent}}
{{hashdefine_lines|autoindent}}
{% endmacro %}
