import pytest
from axiom.mathematics import C, V, Expr, Statement, add, sub, mul, power, evaluate


def test_exact_evaluation_large_integers():
    x = V("x")
    big = 10 ** 70
    assert evaluate(power(add(x, C(1)), 3), {"x": big}) == (big + 1) ** 3


def test_malformed_types_and_out_of_fragment():
    with pytest.raises(ValueError):
        C(True)
    with pytest.raises(ValueError):
        power(V("x"), -1)
    with pytest.raises(ValueError):
        Expr("div", (V("x"), C(2)))
    with pytest.raises(ValueError):
        V("z")
    with pytest.raises(ValueError):
        Statement(V("x"), C(0), "==", ("y",))
    with pytest.raises(ValueError):
        Statement(V("x"), C(0), "==", ("x",), (("x", 2, 1),))
    with pytest.raises(ValueError):
        Expr.from_dict({"op": "pow", "value": 999, "args": [V("x").to_dict()]})


def test_serialization_and_canonicalization():
    a = Statement(add(V("x"), C(1)), C(1), "==", ("x",))
    b = Statement(C(1), add(C(1), V("x")), "==", ("x",))
    assert a.canonical_key() == b.canonical_key()
    assert Statement.from_dict(a.to_dict()) == a
    assert a.holds({"x": 0})
    assert not a.holds({"x": 4})


def test_subtraction_and_zero_power():
    assert evaluate(sub(power(V("x"), 0), C(2)), {"x": 0}) == -1
