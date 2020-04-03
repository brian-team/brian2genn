{# ALLOWS_SCALAR_WRITE #}
{% macro stateupdate_code() %}
// Update "constant over dt" subexpressions (if any)
{{(scalar_code['subexpression_update'] + vector_code['subexpression_update'])|autoindent}}

// PoissonInputs targetting this group (if any)
{{(scalar_code['poisson_input'] + vector_code['poisson_input'])|autoindent}}

// Update state variables and the threshold condition
{{(scalar_code['stateupdate'] + vector_code['stateupdate'])|autoindent}}
{% endmacro %}

{% macro reset_code() %}
{{(scalar_code['reset'] + vector_code['reset'])|autoindent}}
{% endmacro %}

{% macro h_file() %}
{{support_code_lines|autoindent}}
{{hashdefine_lines|autoindent}}
{% endmacro %}
