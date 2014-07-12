from brian2.devices.cpp_standalone.codeobject import CPPStandaloneCodeObject
from brian2.codegen.generators.cpp_generator import c_data_type, CPPCodeGenerator
from brian2.codegen.targets import codegen_targets
from brian2.codegen.templates import Templater

__all__ = ['GeNNCodeObject']


class GeNNCodeObject(CPPStandaloneCodeObject):
    templater = Templater('brian2genn', env_globals={'c_data_type': c_data_type})
    generator_class = CPPCodeGenerator


codegen_targets.add(GeNNCodeObject)
