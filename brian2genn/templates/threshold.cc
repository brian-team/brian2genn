{% macro cpp_file() %}
{% block maincode %}
  {% set code = scalar_code + vector_code %}
  {{code|autoindent|replace("double _cond = ", "")|replace(";", "")}}
{% endblock %}
{% endmacro %}

{% macro h_file() %}
{{support_code_lines|autoindent}}
{% endmacro %}
