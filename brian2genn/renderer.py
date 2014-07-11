from brian2.parsing.rendering import *

__all__ = ['GeNNNodeRenderer']

class GeNNNodeRenderer(NodeRenderer):
    expression_ops = NodeRenderer.expression_ops.copy()
    expression_ops.update({
          # Unary ops
          'Not': '!',
          # Bool ops
          'And': '&&',
          'Or': '||',
          })
    
    def render_BinOp(self, node):
        if node.op.__class__.__name__=='Pow':
            return 'pow(%s, %s)' % (self.render_node(node.left),
                                    self.render_node(node.right))
        else:
            return NodeRenderer.render_BinOp(self, node)

    def render_Name(self, node):
        # Replace Python's True and False with their C++ bool equivalents
        return {'True': 'true',
                'False': 'false'}.get(node.id, node.id)

    def render_Assign(self, node):
        return NodeRenderer.render_Assign(self, node)+';'

