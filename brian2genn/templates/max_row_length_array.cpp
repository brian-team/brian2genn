{# USES_VARIABLES { _synaptic_pre, _synaptic_post, sources, targets,
                    N_incoming, N_outgoing, N,
                    N_pre, N_post, _source_offset, _target_offset }
#}
{# WRITES_TO_READ_ONLY_VARIABLES { N_incoming, N_outgoing}
#}

#include "brianlib/common_math.h"
#include "brianlib/stdint_compat.h"
#include<cmath>
#include<ctime>
#include<iostream>
#include<fstream>
#include<climits>
#include "brianlib/stdint_compat.h"
#include "synapses_classes.h"

////// SUPPORT CODE ///////
namespace {{codeobj_name}}_array {
	{{support_code_lines|autoindent}}
}

////// HASH DEFINES ///////
{{hashdefine_lines|autoindent}}

void _run_{{codeobj_name}}()
{
    using namespace brian;
    using namespace {{codeobj_name}}_array;

    ///// CONSTANTS ///////////
    %CONSTANTS%

    ///// POINTERS ////////////
    {{pointers_lines|autoindent}}
  
    {# Get N_post and N_pre in the correct way, regardless of whether they are
	constants or scalar arrays#}
    const size_t _N_pre = {{constant_or_scalar('N_pre', variables['N_pre'])}};
    const size_t _N_post = {{constant_or_scalar('N_post', variables['N_post'])}};
    {{_dynamic_N_incoming}}.resize(_N_post + _target_offset);
    {{_dynamic_N_outgoing}}.resize(_N_pre + _source_offset);

    for (size_t _idx=0; _idx<_numsources; _idx++) {
      {# After this code has been executed, the arrays _real_sources and
	  _real_targets contain the final indices. Having any code here it all is
	  only necessary for supporting subgroups #}
      {{vector_code|autoindent}}

      // Update the number of total outgoing/incoming synapses per source/target neuron
      {{_dynamic_N_outgoing}}[_real_sources]++;
      {{_dynamic_N_incoming}}[_real_targets]++;
    }
 }

