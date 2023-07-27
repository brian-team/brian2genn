Brian2GeNN
==========
Brian2GeNN is an interface between Brian 2 and GeNN. Brian2 is a simulator for spiking neural networks available on a variety of platforms. It is the successor of Brian1 and shares its approach of being highly flexible and easily extensible. It is based on a code generation framework that allows to execute simulations using other programming languages and/or on different
devices. 

GeNN (GPU enhanced Neuronal Networks, https://github.com/genn-team/genn) is a framework that uses code generation methods to allow using GPU accelerators without in-depth knowledge of the CUDA programming interface.

Brian2Genn provides an interface to use GeNN as a backend device in Brian2. This allows users to run their Brian 2 scripts on NVIDIA GPU accelerators without any further necessary programming.

We currently consider this software to be in the beta status, please report
issues to the github issue tracker (https://github.com/brian-team/brian2genn/issues).

Documentation for Brian2GeNN can be found at http://brian2genn.readthedocs.org

[![PyPI package](https://img.shields.io/pypi/v/Brian2GeNN.svg)](https://pypi.python.org/pypi/Brian2GeNN)
[![Documentation Status](https://readthedocs.org/projects/brian2genn/badge/?version=stable)](https://brian2genn.readthedocs.io/en/stable/?badge=stable)
[![Build Status](https://github.com/brian-team/brian2genn/actions/workflows/testsuite.yml/badge.svg)](https://github.com/brian-team/brian2genn/actions/workflows/testsuite.yml)

If you use BrianGeNN for your published research, we kindly ask you to cite our article:  
Marcel Stimberg, Dan F. M. Goodman, and Thomas Nowotny. “Brian2GeNN: Accelerating Spiking Neural Network Simulations with Graphics Hardware.” Sci Rep 10 (January 2020): 410. [doi: 10.1038/s41598-019-54957-7](https://doi.org/10.1038/s41598-019-54957-7).
