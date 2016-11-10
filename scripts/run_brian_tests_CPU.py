import sys

import brian2genn
import brian2

if __name__ == '__main__':
    success = brian2.test([], test_codegen_independent=False,
                          test_standalone='genn',
                          build_options={'use_GPU': False},
                          fail_for_not_implemented=False)
    if not success:
        sys.exit(1)
