import operator

from sympy import Add, Expr, Number, Mul, Pow, S, Symbol
from sympy.core.decorators import call_highest_priority

# from tensor import Tensor /* cyclic */
# from functions import Inner, Inverse, Transpose /* cyclic */

class ConformityError (Exception):
    pass

class TensorExpr (Expr):
    """Base object for things with Tensor properties such as:
    
        * rank
        * shape
        * has_inverse
        * algebraic ops 
    
    """
    _op_priority = 20
    rank = -1
    name = None
    has_inverse = False
    shape = None
    is_symmetric = True

    def __mul_by_one (self, other):
        self_is_one = is_one(self)
        other_is_one = is_one(other)
        if self_is_one or other_is_one:
            ers = expr_rank(self)
            ero = expr_rank(other)
            if ers == ero == 2:
                return other if self_is_one else self
            if self_is_one and ers == 0:
                return other
            if other_is_one and ero == 0:
                return self

    @call_highest_priority('__rmul__')
    def __mul__ (self, other):
        is_mul_conforming_or_die(self, other)
        if is_zero(self) or is_zero(other):
            return Tensor('0', rank=mul_rank(self, other))
        if is_inner(self, other):
            return Inner(self, other)
        mul_by_one = self.__mul_by_one(other)
        if mul_by_one is not None:
            return mul_by_one
        return super(TensorExpr, self).__mul__(other)

    @call_highest_priority('__mul__')
    def __rmul__ (self, other):
        is_mul_conforming_or_die(other, self)
        if is_zero(self) or is_zero(other):
            return Tensor('0', rank=mul_rank(other, self))
        if is_inner(other, self):
            return Inner(other, self)
        mul_by_one = self.__mul_by_one(other)
        if mul_by_one is not None:
            return mul_by_one
        return super(TensorExpr, self).__rmul__(other)

    @call_highest_priority('__radd__')
    def __add__ (self, other):
        is_add_conforming_or_die(self, other)
        if is_zero(self):
            return other
        if is_zero(other):
            return self
        return super(TensorExpr, self).__add__(other)

    @call_highest_priority('__add__')
    def __radd__ (self, other):
        is_add_conforming_or_die(other, self)
        if self.name and self.name.startswith('0'):
            return other
        return super(TensorExpr, self).__radd__(other)

    @call_highest_priority('__rsub__')
    def __sub__ (self, other):
        if is_zero(self):
            return - other
        if is_zero(other):
            return self
        return super(TensorExpr, self).__sub__(other)

    @call_highest_priority('__sub__')
    def __rsub__ (self, other):
        if is_zero(self):
            return other
        if is_zero(other):
            return - self
        return super(TensorExpr, self).__rsub__(other)

    @call_highest_priority('__rdiv__')
    def __div__ (self, other):
        if is_zero(self):
            raise ZeroDivisionError()
        if isinstance(other, TensorExpr):
            return Mul(self, Inverse(other))
        return super(TensorExpr, self).__div__(other)

    @call_highest_priority('__div__')
    def __rdiv__ (self, other):
        if is_zero(self):
            raise ZeroDivisionError()
        return Mul(other, Inverse(self))

    @call_highest_priority('__rpow__')
    def __pow__ (self, other):
        if is_zero(self):
            return self
        if is_one(self):
            return self
        elif isinstance(other, int) and other < 0:
            return Inverse(self) ** (-other)
        else:
            return Pow(self, other)

    @call_highest_priority('__pow__')
    def __rpow__ (self, other):
        raise RuntimeError("Can't raise to the tensor power.")

    def __neg__(self):
        if is_zero(self):
            return self
        return super(TensorExpr, self).__neg__()

def is_zero (expr):
    """Returns True, False, or None"""
    if isinstance(expr, Tensor):
        return expr.name.startswith('0')
    if isinstance(expr, Transpose):
        return is_zero(expr.args[0])
    if expr == S(0):
        return True

def is_one (expr):
    """Returns True, False, or None"""
    if isinstance(expr, Tensor):
        return expr.name.startswith('1')
    if isinstance(expr, Transpose):
        return is_one(expr.args[0])
    if expr == S(1):
        return True

def is_outer (a, b):
    esa = expr_shape(a)
    esb = expr_shape(b)
    return expr_rank(a) == expr_rank(b) == 1 and \
           esa[1] == esb[0] == 1 and esa[0] == esb[1]

def is_inner (a, b):
    esa = expr_shape(a)
    esb = expr_shape(b)
    return expr_rank(a) == expr_rank(b) == 1 and \
           esa[0] == esb[1] == 1 and esa[1] == esb[0]

def is_mul_conforming_or_die (a, b):
    esa = expr_shape(a)
    esb = expr_shape(b)
    if (1, 1) in [esa, esb]:
        return True
    if expr_shape(a)[1] != expr_shape(b)[0]:
        raise ConformityError("%s * %s\n\tranks %d, %d\n\tshapes %s, %s"\
                              % (str(a), str(b), expr_rank(a), expr_rank(b),
                                 str(expr_shape(a)), str(expr_shape(b))))
    return True

def is_add_conforming_or_die (a, b):
    if a in [S(0), S(1)] or b in [S(0), S(1)]:
        return True
    if expr_rank(a) != expr_rank(b) and expr_shape(a) != expr_shape(b):
        raise ConformityError("%s + %s\n\tranks %d, %d\n\tshapes %s, %s"\
                              % (str(a), str(b), expr_rank(a), expr_rank(b),
                                 str(expr_shape(a)), str(expr_shape(b))))
    return True

def mul_rank (a, b):
    if is_outer(a, b):
        return 2
    era = expr_rank(a)
    erb = expr_rank(b)
    if era == 0 or erb == 0:
        return max(era, erb)
    return era + erb - 2

def expr_shape(expr):
    """Returns the shape of a given expression

    Will raise ConformityError if expression does not conform.
    
    >>> A = Tensor('A', rank=2)
    >>> B = Tensor('B', rank=2)
    >>> x = Tensor('x', rank=1)
    >>> expr_shape(A+B)
    (n, n)
    >>> expr_shape((A+B)*x)
    (n, 1)
    >>> expr_shape(A*T(x))
    ---------------------------------------------------------------------------
    ConformityError                           Traceback (most recent call last)
    """
    if isinstance(expr, TensorExpr):
        return expr.shape
    if isinstance(expr, (Number, Symbol, int, long, float)):
        return (1, 1)
    if isinstance(expr, Add):
        #TODO: Check consistency
        return expr_shape(expr.args[0])
    if isinstance(expr, Mul):
        arg_shapes = map(expr_shape, expr.args)
        arg_shapes = filter(lambda x: x != (1, 1), arg_shapes)
        if len(arg_shapes) == 0:
            return (1, 1)
        return (arg_shapes[0][0], arg_shapes[-1][1])
    if isinstance(expr, Pow):
        if expr_rank(expr.args[0]) == 1:
            raise ConformityError()
        return expr_shape(expr.args[0])
    raise NotImplementedError("expr_shape can't handle: %s of type: %s" % \
                              (str(expr), type(expr)))

def expr_rank(expr):
    """Returns the rank of a given expression

    Will raise ConformityError if expression does not conform.
    
    >>> A = Tensor('A', rank=2)
    >>> B = Tensor('B', rank=2)
    >>> x = Tensor('x', rank=1)
    >>> expr_rank(A+B)
    2
    >>> expr_rank((A+B)*x)
    1
    >>> expr_rank(A*T(x))
    ---------------------------------------------------------------------------
    ConformityError                           Traceback (most recent call last)
    """

    if isinstance(expr, TensorExpr):
        return expr.rank
    if isinstance(expr, (Number, int, float)):
        return 0
    if isinstance(expr, Add):
        #TODO: Check consistency
        return expr_rank(expr.args[0])
    if isinstance(expr, Mul):
        arg_shape = expr_shape(expr)
        return sum(map(lambda x: x != 1, arg_shape))
    if isinstance(expr, Pow):
        if isinstance(expr.args[1], (Number, int)):
            base_rank = expr_rank(expr.args[0])
            if expr.args[1] == -1:
                return base_rank
            if base_rank == 0 or base_rank == 2:
                return base_rank
            if base_rank == 1 and expr.args[1] % 2 == 0:
                return 0
            if base_rank == 1:
                return 1
    raise NotImplementedError("expr_rank can't handle: %s of type: %s" % \
                              (str(expr), type(expr)))

def expr_coeff(expr, var):
    if not isinstance(expr, Mul):
        return expr
    if len(filter(lambda x: var in x, expr.args)) != 1:
        raise ValueError("Can't handle eqns with more than one of var, given %s, %s"\
                         % (expr, var))
    for idx, e in enumerate(expr.args):
        if var in e:
            break
    lhs = expr.args[:idx]
    rhs = expr.args[idx + 1:] if len(expr.args) > idx + 1 else []
    return reduce(operator.mul, lhs, S(1)), expr.args[idx], reduce(operator.mul, rhs, S(1))


from tensor import Tensor #/* cyclic */
from basic_operators import Inner, Inverse, Transpose
