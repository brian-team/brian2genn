{% block maincode %}
  {% set code = scalar_code + vector_code %}
  {{code|autoindent|replace("double _cond = ", "")|replace(";", "")}}
{% endblock %}
