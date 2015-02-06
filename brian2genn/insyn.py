'''
GeNN accumulates postsynaptic changes into a variable inSyn. The idea of this
module is to check, for a given Synapses, whether or not it can be recast into
this formulation, and if so to relabel the variables appropriately.

In GeNN, each synapses object has an associated variable inSyn. The idea is
that we will do something like this in Brian terms:

    v += w (synapses code)
    dv/dt = -v/tau (neuron code)

should be replaced by:

    inSyn += w (synapses code)
    dv/dt = -v/tau (neuron code)
    v += inSyn; inSyn = 0; (custom operation carried out after integration step)
    
In GeNN terms these are labelled differently (Thomas, maybe explain this point
here).

The conditions for this rewrite to be possible are as follows for presynaptic
event code:
- Each expression is allowed to modify synaptic variables.
- An expression can modify a neuron variable only in the following ways:
     neuron_var += expr (where expr contains only synaptic variables)
     neuron_var = expr (where expr-neuron_var can be simplified to contain only synaptic variables)
- The set of modified neuron variables can only have one element
And for the postsynaptic code, only synaptic variables can be modified.

The output of this code should be:
- Raise an error if it is not possible, explaining why
- Replace the line neuron_var (+)= expr with addtoinSyn = new_expr
- Return neuron_var so that it can be used appropriately in GeNNDevice.build

The GeNN syntax is:

    addtoinSyn = expr


Brian codegen implementation:

I think the correct place to start is given a Statement sequence for a 
Synapses pre or post code object, check the conditions. Then, we need to create
two additional CodeObjects which overwrite translate_one_statement_sequence to
call this function and rewrite the appropriate statement.
'''
from brian2.utils.stringtools import get_identifiers
from brian2.codegen.statements import Statement

def check_pre_code(codegen, stmts, vars_pre, vars_syn, vars_post):
    '''
    Given a set of statements stmts where the variables names in vars_pre are
    presynaptic, in vars_syn are synaptic and in vars_post are postsynaptic,
    check that the conditions for compatibility with GeNN are met, and return
    a new statement sequence translated for compatibility with GeNN, along
    with the name of the targeted variable.
    '''
    read, write, indices = codegen.array_read_write(stmts)
    
    post_write = set(write).intersection(set(vars_post))
    if len(post_write)==0:
        raise NotImplementedError("GeNN does not support Synapses with no postsynaptic effect.")
    if len(post_write)>1:
        raise NotImplementedError("GeNN only supports writing to a single postsynaptic variable.")
    
    post_write_var = list(post_write)[0]
    
    # pre_write = set(write).intersection(set(vars_pre))
    # if len(pre_write):
    #     raise NotImplementedError("GeNN does not support writing to presynaptic variables.")
    
    found_write_statement = False
    new_stmts = []
    for stmt in stmts:
        ids = get_identifiers(stmt.expr)
        if stmt.var==post_write_var:
            if stmt.inplace:
                if stmt.op!='+=':
                    raise NotImplementedError("GeNN only supports the += in place operation on postsynaptic variables.")
#                 if set(ids).intersection(set(vars_pre).union(set(vars_post))):
#                     raise NotImplementedError("GeNN only supports postsynaptic operations using only synaptic variables.")
                accumulation_expr = stmt.expr
            else:
                # TODO: we could support expressions like v = v + expr, but this requires some additional work
                # namely, for an expression like v = expr we need to check if (expr-v) when simplified reduces to
                # an expression that only has postsynaptic variables using sympy
                raise NotImplementedError("GeNN only supports in-place modification of postsynaptic variables")
            new_stmt = Statement('addtoinSyn', '=', '_hidden_weightmatrix*('+accumulation_expr+')',
                                 comment=stmt.comment, dtype=stmt.dtype)
            new_stmts.append(new_stmt)
            if found_write_statement:
                raise NotImplementedError("GeNN does not support multiple writes to postsynaptic variables.")
            found_write_statement = True
        else:
            new_stmts.append(stmt)
    
    return post_write_var, new_stmts


def check_post_code(codegen, stmts, vars_pre, vars_syn, vars_post):
    read, write, indices = codegen.array_read_write(stmts)

#     post_write = set(write).intersection(set(vars_post))
#     if len(post_write):
#         raise NotImplementedError("GeNN does not support writing to postsynaptic variables in postsynaptic code.")
    
#     pre_write = set(write).intersection(set(vars_pre))
#     if len(pre_write):
#         raise NotImplementedError("GeNN does not support writing to presynaptic variables in postsynaptic code.")
