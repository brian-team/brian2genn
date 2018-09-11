import sys

import brian2genn
import brian2

import numpy as np

if __name__ == '__main__':
    success = brian2.test([], test_codegen_independent=False,
                          test_standalone='genn',
                          fail_for_not_implemented=False,
                          float_dtype=np.float32)
    if not success:
        sys.exit(1)
