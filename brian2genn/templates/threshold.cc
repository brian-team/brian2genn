{% block maincode %}
{{ vector_code|autoindent|replace('_cond = ', '') }}
{% endblock %}