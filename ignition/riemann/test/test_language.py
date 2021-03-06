from ignition.riemann.language import *

def test_construction():
    """Test construction of Riemann expressions"""
    q = Conserved('q')
    h, uh = q.fields('h', 'uh')
    assert(h == Field('h'))
    assert(uh == Field('uh'))
    g = Constant('g')
    u = uh / h
    expr = u * uh + .5 * g * h ** 2
    assert(str(expr) == '0.5*h**2*g + uh**2/h')
