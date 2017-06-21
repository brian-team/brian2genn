from brian2 import prefs
prefs.logging.std_redirection = False

import brian2genn
brian2genn.example_run(use_GPU=False)
