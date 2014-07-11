import os

from brian2.core.variables import Variable, Subexpression
from brian2.codegen.codeobject import CodeObject
from brian2.codegen.templates import Templater
from .genn_generator import GeNNCodeGenerator

__all__ = ['GeNNCodeObject']


class GeNNCodeObject(CodeObject):
    '''
    GeNN code object
    
    The ``code`` should be a `~brian2.codegen.languages.templates.MultiTemplate`
    object with two macros defined, ``model`` (for the model definition) and
    ``runner`` for user-side code.
    '''
    templater = Templater(os.path.join(os.path.split(__file__)[0],
                                       'templates'))
    generator_class = GeNNCodeGenerator
    class_name = 'genn'

    def variables_to_namespace(self):
        # We only copy constant scalar values to the namespace here
        for varname, var in self.variables.iteritems():
            if var.constant and var.scalar:
                self.namespace[varname] = var.get_value()

    def run(self):
        raise RuntimeError("Cannot run in GeNN mode")
