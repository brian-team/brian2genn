from brian2.core.preferences import *
'''
Preferences that relate to the brian2genn interface.
'''

def valid_connectivity(value):
    for v in ['DENSE', 'SPARSE', 'AUTO']:
        if value == v:
            return True
    return False

def valid_connectivity_decision(expr):
    Npre= 10
    Npost= 10
    Nsyn= 50
    try:
        val= eval(expr)
    except Exception:
        return False
    if val == True or val == False:
        return True
    return False
    

prefs.register_preferences(
    'devices.genn',
    'Preferences that relate to the brian2genn interface',
    connectivity= BrianPreference(
        validator= valid_connectivity,
        docs='''
        This preference determines which connectivity scheme is to be employed within GeNN. The valid alternatives are 'DENSE', 'SPARSE', and 'AUTO'. For 'DENSE' the GeNN dense matrix methods are used for all connectivity matrices. When 'SPARSE' is chosen, the GeNN sparse matrix representations are used. For 'AUTO', GeNN decides on a per-synapse population basis whether to use dense or sparse representations based on the evaluation of a decision function that returns whether to use dense or sparse methods based on the number of pre-synaptic neurons, post-synaptic neurons and the number of existing connections. The default decision function chooses sparse methods whenever, the number of existing connections  is less than 25% of all possible connections. A custom decision expression can be provided with the preference 'connectivity_decision'.''',
        default= 'DENSE'
    ),
    connectivity_decision= BrianPreference(
        validator= valid_connectivity_decision,
        docs= '''
        This preference allows users to set their own logical expression for the decision whether to use dense or sparse matrix methods based on Npre, Npost and Nsyn. Users should provide a valid Python expression that involves the variable sNpre (pre-synaptic neurons number), Npost (post-synaptic neuron number) and Nsyn (number of existing synapses) and return <True> for using dense matrices and <False> for using sparse. The default behaviour, e.g., corresponds to the logical expression 'Nsyn > 0.25*Npre*Npost'. ''',
        default= 'Nsyn > 0.25*Npre*Npost'
    )
)

    
  
        
