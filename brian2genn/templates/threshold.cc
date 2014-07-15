{% block maincode %}
{{ vector_code|autoindent|replace("double _cond = ", "")|replace(";", "")}}
{% endblock %}
