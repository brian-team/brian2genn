{% macro stateupdate_code() %}
// Update "constant over dt" subexpressions (if any)
{{(scalar_code['subexpression_update'] + vector_code['subexpression_update'])|autoindent}}
{% if has_run_regularly %}

// Run regular operations on a slower clock
if (fabs(fmod(t, _run_regularly_dt)) < dt/2) {
    {{(scalar_code['run_regularly'] + vector_code['run_regularly'])|autoindent}}
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

{% macro subexpression_update_code() %}
{{(scalar_code['subexpression_update'] + vector_code['subexpression_update'])|autoindent}}
{% endmacro %}


{% macro h_file() %}
{{support_code_lines|autoindent}}
{{hashdefine_lines|autoindent}}
{% endmacro %}
