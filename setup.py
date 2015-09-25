#! /usr/bin/env python
'''
Brian2GeNN setup script
'''
import sys
import os
import platform

if sys.version_info < (2, 7):
    raise RuntimeError('Only Python versions >= 2.7 are supported')

from pkg_resources import parse_version
from setuptools import setup, find_packages, Extension
from setuptools.command.build_ext import build_ext
from distutils.errors import CompileError, DistutilsPlatformError

long_description = '''
Brian2GeNN is an interface between Brian 2 and GeNN. Brian2 is a simulator for spiking neural networks available on a variety of platforms. It is the successor of Brian1 and shares its approach of being highly flexible and easily extensible. It is based on a code generation framework that allows to execute simulations using other programming languages and/or on different
devices. 

GeNN (GPU enhanced Neuronal Networksm, https://github.com/genn-team/genn) is a framework that uses code generation methods to allow using GPU accelerators without in-depth knowledge of the CUDA programming interface.

Brian2Genn provides an interface to use GeNN as a backend device in Brian2. This allows users to run their Brian 2 scripts on NVIDIA GPU accelerators without any further necessary programming.

We currently consider this software to be in the beta status, please report
issues to the github issue tracker (https://github.com/brian-team/brian2genn/issues).

Documentation for Brian2GeNN can be found at http://brian2genn.readthedocs.org
'''

setup(name='Brian2GeNN',
      version='0.9b',
      packages= ['brian2genn', 'brian2genn.sphinxext'], #find_packages(),
      package_data={# include template files
                    'brian2genn': ['templates/*.cpp',
                                   'templates/*.h',
                                   'templates/*.cc',
                                   'templates/WINmakefile',
                                   'templates/GNUmakefile',
                                   'b2glib/*.cpp',
                                   'b2glib/*.h'],
      },
      install_requires=[
#'numpy>=1.8.0',
#                        'sympy>=0.7.6',
#                        'pyparsing',
                        'jinja2>=2.7',
                        'setuptools>=6.0',  # FIXME: setuptools>=6.0 is only needed for Windows
                        'brian2==2.0b4'
                       ],
      dependency_links=["https://github.com/brian-team/brian2/tarball/fd3afff2be7b506d8aa76e6fd2259f888fa40ba0#egg=brian2-2.0b4"],
      setup_requires=[
#'numpy>=1.8.0',
                      'setuptools>=6.0'
                      ],
      provides=['brian2genn'],
      extras_require={'docs': ['sphinx>=1.0.1', 'sphinxcontrib-issuetracker']},
      use_2to3=True,
      url='http://www.briansimulator.org/',
      description='An interface to use the GeNN framework as a device in Brian 2',
      long_description=long_description,
      author='Thomas Nowotny, Marcel Stimberg, Dan Goodman',
      author_email='t.nowotny at sussex.ac.uk',
      classifiers=[
          'Development Status :: 1 - Beta',
          'Intended Audience :: Science/Research',
          'License :: GPL',
          'Natural Language :: English',
          'Operating System :: OS Independent',
          'Programming Language :: Python',
          'Programming Language :: Python :: 2',
          'Programming Language :: Python :: 3',
          'Topic :: Scientific/Engineering :: Bio-Informatics'
      ]
      )
