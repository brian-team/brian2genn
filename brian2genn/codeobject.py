from brian2.devices.cpp_standalone.codeobject import CPPStandaloneCodeObject, openmp_pragma, constant_or_scalar
from brian2.codegen.generators.cpp_generator import c_data_type, CPPCodeGenerator
from brian2.codegen.targets import codegen_targets
from brian2.codegen.templates import Templater
from .genn_generator import *

__all__ = ['GeNNCodeObject',
           'GeNNUserCodeObject']    

class GeNNCodeObject(CPPStandaloneCodeObject):
    templater = Templater('brian2genn', env_globals={'c_data_type': c_data_type,
                                                     'openmp_pragma': openmp_pragma,
                                                     'constant_or_scalar': constant_or_scalar})
    generator_class = GeNNCodeGenerator

class GeNNUserCodeObject(CPPStandaloneCodeObject):
    templater = Templater('brian2genn', env_globals={'c_data_type': c_data_type,
                                                     'openmp_pragma': openmp_pragma,
                                                     'constant_or_scalar': constant_or_scalar})
    generator_class = CPPCodeGenerator

codegen_targets.add(GeNNCodeObject)
codegen_targets.add(GeNNUserCodeObject)
