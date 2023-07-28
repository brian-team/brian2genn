import sys

import brian2genn
import brian2

import test_utils
skip_args = test_utils.get_skip_args()

if __name__ == '__main__':
    success = brian2.test([], test_codegen_independent=False,
                          test_standalone='genn',
                          fail_for_not_implemented=False,
                          additional_args=skip_args)
    if not success:
        sys.exit(1)