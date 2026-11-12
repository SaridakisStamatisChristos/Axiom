import pytest
from axiom.mathematics import C, V, Statement, add, sub, mul, power
from axiom.verification import falsify, polynomial_proof


def test_binomial_identity_has_exact_proof_certificate():
    x = V("x")
    statement = Statement(power(add(x, C(2)), 2), add(add(power(x, 2), mul(C(4), x)), C(4)), "==", ("x",))
    proof = polynomial_proof(statement)
    assert proof and proof["coefficient_difference"] == []
    assert falsify(statement, -4, 4, 100, 1)["counterexample"] is None


def test_distributive_multivariate_proof():
    x, y = V("x"), V("y")
    statement = Statement(mul(x, add(y, C(7))), add(mul(x, y), mul(C(7), x)), "==", ("x", "y"))
    assert polynomial_proof(statement) is not None


def test_false_relation_and_independent_counterexample():
    x = V("x")
    statement = Statement(power(add(x, C(2)), 2), add(add(power(x, 2), mul(C(4), x)), C(5)), "==", ("x",))
    assert polynomial_proof(statement) is None
    evidence = falsify(statement, -3, 3, 20, 2)
    assert evidence["counterexample"] is not None
    assert not statement.holds(evidence["counterexample"])
    assert statement.assumption_holds(evidence["counterexample"])


def test_inequality_excluded_zero_and_bounded_support_only():
    x = V("x")
    false_at_zero = Statement(x, C(1), ">=", ("x",), (("x", 0, 3),))
    assert falsify(false_at_zero, -100, 100, 20, 5)["counterexample"] == {"x": 0}
    positive = Statement(x, C(1), ">=", ("x",), (("x", 1, 3),))
    search = falsify(positive, -100, 100, 20, 5)
    assert search["counterexample"] is None and search["exhaustive"]
    assert polynomial_proof(positive) is None


def test_budget_does_not_mean_proof():
    x = V("x")
    statement = Statement(power(x, 2), C(0), ">=", ("x",))
    search = falsify(statement, -100, 100, 2, 1)
    assert search["counterexample"] is None
    assert search["tested"] == 2 and search["exhaustive"] is False
    assert polynomial_proof(statement) is None


def test_reject_non_poly_operator_and_invalid_bounds():
    with pytest.raises(ValueError):
        Statement(V("x"), C(0), ">", ("x",))
    with pytest.raises(ValueError):
        Statement(V("x"), C(0), "==", ("x",), (("x", 1, -1),))


def test_randomized_algebraic_normalizers_agree():
    import random
    x, y = V("x"), V("y")
    rng = random.Random(2026)
    for _ in range(60):
        a, b, c = (rng.randint(-10, 10) for _ in range(3))
        lhs = mul(add(mul(C(a), x), C(b)), add(y, C(c)))
        rhs = add(add(mul(mul(C(a), x), y), mul(C(a * c), x)), add(mul(C(b), y), C(b * c)))
        assert polynomial_proof(Statement(lhs, rhs, "==", ("x", "y"))) is not None
        wrong = add(rhs, C(1))
        assert polynomial_proof(Statement(lhs, wrong, "==", ("x", "y"))) is None
