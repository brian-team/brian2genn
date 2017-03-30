{# ALLOWS_SCALAR_WRITE #}
{% macro stateupdate_code() %}
// Update "constant over dt" subexpressions (if any)
{{(scalar_code['subexpression_update'] + vector_code['subexpression_update'])|autoindent}}

{% if has_run_regularly %}
// Run regular operations on a slower clock
int _timesteps = (int)(t/dt + 0.5);
if (_timesteps % (int)_run_regularly_steps == 0) {  {# we need a type cast because GeNN parameters are double values #}
    {{vector_code['run_regularly']|autoindent}}  {# Note that the scalar code (if any) is in a separate code object #}
}
{% endif %}

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
