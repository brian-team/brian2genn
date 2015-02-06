from brian2.devices.cpp_standalone.codeobject import CPPStandaloneCodeObject, openmp_pragma
from brian2.codegen.generators.cpp_generator import c_data_type, CPPCodeGenerator
from brian2.codegen.targets import codegen_targets
from brian2.codegen.templates import Templater
from brian2genn.insyn import check_pre_code, check_post_code

__all__ = ['GeNNCodeObject',
           'GeNNUserCodeObject']


# Don't generate any code for reading from/writing to arrays or
# variable declarations
class GeNNCodeGenerator(CPPCodeGenerator):

    def translate_to_read_arrays(self, statements):
        return []

    def translate_to_write_arrays(self, statements):
        return []

    def translate_to_declarations(self, statements):
        return []

    def translate_statement(self, statement):
        var, op, expr, comment = (statement.var, statement.op,
                                  statement.expr, statement.comment)
        # for debugging only: show translated statements
        print(var,op,expr,comment);
        if op == ':=':
            decl= self.c_data_type(statement.dtype) + ' '
            op = '='
        else:
            decl= ''
        code = decl + var + ' ' + op + ' ' + self.translate_expression(expr) + ';'
        if len(comment):
            code += ' // ' + comment
        return code
    
    def translate_one_statement_sequence(self, statements):
        if len(statements) and self.template_name=='synapses':
            print '*****************', self.template_name, self.name, self.owner.name
            print 'PRETRANSLATION oh yeah'
            for statement in statements:
                print '   ', statement
            vars_pre = [k for k, v in self.variable_indices.items() if v=='_presynaptic_idx']
            vars_syn = [k for k, v in self.variable_indices.items() if v=='_idx']
            vars_post = [k for k, v in self.variable_indices.items() if v=='_postsynaptic_idx']
            print 'VARS_PRE', vars_pre
            print 'VARS_SYN', vars_syn
            print 'VARS_POST', vars_post
            if '_pre_codeobject' in self.name:
                post_write_var, statements = check_pre_code(self, statements,
                                                vars_pre, vars_syn, vars_post)
                print 'POST_WRITE_VAR', post_write_var
                self.owner._genn_post_write_var = post_write_var
            elif '_post_codeobject' in self.name:
                check_post_code(self, statements, vars_pre, vars_syn, vars_post)
            print 'POSTTRANSLATION'
            for statement in statements:
                print '   ', statement
        return CPPCodeGenerator.translate_one_statement_sequence(self, statements)


class GeNNCodeObject(CPPStandaloneCodeObject):
    templater = Templater('brian2genn', env_globals={'c_data_type': c_data_type,
                                                     'openmp_pragma': openmp_pragma})
    generator_class = GeNNCodeGenerator

class GeNNUserCodeObject(CPPStandaloneCodeObject):
    templater = Templater('brian2genn', env_globals={'c_data_type': c_data_type,
                                                     'openmp_pragma': openmp_pragma})
    generator_class = CPPCodeGenerator

codegen_targets.add(GeNNCodeObject)
codegen_targets.add(GeNNUserCodeObject)
