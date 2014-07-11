import os

from brian2.core.variables import Variable, Subexpression
from brian2.codegen.codeobject import CodeObject
from brian2.codegen.targets import codegen_targets
from brian2.codegen.templates import Templater
from .genn_generator import GeNNCodeGenerator, c_data_type

__all__ = ['GeNNCodeObject']


class GeNNCodeObject(CodeObject):
    '''
    GeNN code object
    
    The ``code`` should be a `~brian2.codegen.languages.templates.MultiTemplate`
    object with two macros defined, ``model`` (for the model definition) and
    ``runner`` for user-side code.
    '''
    templater = Templater('brian2genn', env_globals={'c_data_type': c_data_type})
    generator_class = GeNNCodeGenerator

    def __call__(self, **kwds):
        return self.run()

    def run(self):
        get_device().main_queue.append(('run_code_object', (self,)))


codegen_targets.add(GeNNCodeObject)
