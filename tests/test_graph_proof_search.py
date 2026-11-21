from copy import deepcopy
from fractions import Fraction
from itertools import combinations, product

import pytest

from axiom.graph_affine import AffineGraphConjecture
from axiom.graph_claims import digest
from axiom.graph_proof import BANK, PINNED_MATHLIB_SHA, audit, prove
from axiom.graph_proof_search import LemmaSpec, SearchLimits, search
from axiom.graph_relations import AffineRelation, _vector


def relation(weights, rhs=0, premise="ALL", op="<="):
    return AffineRelation.normalized(weights, rhs, premise, op)


def test_wider_schema_preserves_legacy_identity_and_semantics():
    weights = {"clique": 1, "chromatic": -1, "components": 1, "n": -1}
    original = relation(weights)
    scaled = relation({k: Fraction(v, 2) for k, v in reversed(weights.items())} | {"edges": 0})
    assert original.id == scaled.id
    assert original.id != relation({k: -v for k, v in weights.items()}).id
    assert AffineRelation.from_dict(original.to_dict()) == original
    with pytest.raises(ValueError):
        AffineGraphConjecture.from_dict(original.bound.to_dict())
    with pytest.raises(ValueError):
        relation({"clique": 0})
    with pytest.raises(ValueError):
        relation({"clique": 1.0})
    with pytest.raises(ValueError):
        relation(dict.fromkeys(("n", "edges", "clique", "components", "matching",
                                "independence", "chromatic"), 1))


@pytest.mark.parametrize("premise", ["ALL", "CONNECTED", "TRIANGLE_FREE", "BIPARTITE"])
def test_shortest_search_matches_independent_exhaustive_oracle(premise):
    allowed = sorted((x for x in BANK if x.premise in ("ALL", premise)), key=lambda x: x.theorem)
    limits = SearchLimits(3, 2)
    oracle = {}
    for size in range(1, 4):
        for subset in combinations(allowed, size):
            for coefficients in product((1, 2), repeat=size):
                vector = tuple(sum(coeff * entry for coeff, entry in zip(coefficients, coordinate))
                               for coordinate in zip(*(x.vector for x in subset)))
                rhs = sum(coef * lemma.rhs for coef, lemma in zip(coefficients, subset))
                ids = tuple((lemma.theorem, coefficient) for lemma, coefficient in zip(subset, coefficients))
                oracle.setdefault(vector, []).append((size, ids, rhs))
    for vector, derivations in oracle.items():
        weights = {k: v for k, v in zip(("n", "edges", "triangles", "independence", "clique",
                                         "chromatic", "maximum_degree", "matching", "components"), vector) if v}
        if not weights or len(weights) > 6:
            continue
        claim = relation(weights, min(row[2] for row in derivations), premise)
        target = _vector(claim.bound.terms)
        choices = [row for row in oracle.get(target, ()) if row[2] <= claim.bound.upper]
        result = search(claim, BANK, limits)
        assert result == search(claim, tuple(reversed(BANK)), limits)
        assert result["derived"] is bool(choices)
        if choices:
            used = result["directions"][0]["lemmas"]
            assert tuple((x["theorem"], x["coefficient"]) for x in used) == min(choices)[1]


def test_premise_and_bidirectional_equality_rules():
    weights = {"maximum_degree": 1, "independence": -1}
    for premise in ("ALL", "CONNECTED", "BIPARTITE"):
        assert not search(relation(weights, premise=premise), BANK, SearchLimits())["derived"]
    assert search(relation(weights, premise="TRIANGLE_FREE"), BANK, SearchLimits())["derived"]
    equality = relation({"clique": 1, "chromatic": -1}, op="=")
    result = search(equality, BANK, SearchLimits())
    assert not result["derived"]
    assert sum(d["lemmas"] is not None for d in result["directions"]) == 1

    side = _vector(equality.bound.terms)
    synthetic = (LemmaSpec("a", "ALL", side, 0),
                 LemmaSpec("b", "ALL", tuple(-x for x in side), 0))
    assert search(equality, synthetic, SearchLimits())["derived"]


def test_budget_and_semantic_invalidity_are_not_refutations():
    target = relation({"clique": 1, "chromatic": -1, "components": 1, "n": -1})
    result = prove(target.to_dict(), limits=SearchLimits(max_nodes=1))
    assert result["status"] == "SEARCH_EXHAUSTED"
    assert result["reason"] == "NODE_BUDGET_EXHAUSTED"
    assert result["derivation"]["nodes"] == 1 and audit(result)
    malformed = target.to_dict()
    malformed["bound"]["assumption"] = "CONNECTED AND TRIANGLE_FREE"
    report = prove(malformed)
    assert report["status"] == "UNSUPPORTED" and report["reason"] == "UNSUPPORTED_PREMISE"
    assert audit(report)


def test_missing_and_dummy_lean_cannot_verify(monkeypatch, tmp_path):
    target = relation({"clique": 1, "chromatic": -1}).to_dict()
    from axiom import graph_affine_lean_n3 as backend

    (tmp_path / "lean-toolchain").write_text(backend.TOOLCHAIN)
    (tmp_path / "lakefile.toml").write_text(
        '[[require]]\nname = "mathlib"\nscope = "leanprover-community"\n'
        f'rev = "{backend.MATHLIB_REV}"\n')
    monkeypatch.setenv("PATH", str(tmp_path))
    assert prove(target, project_root=tmp_path)["status"] == "LEAN_UNAVAILABLE"
    dummy = tmp_path / "lake"
    dummy.write_text('#!/bin/sh\nexit 0\n')
    dummy.chmod(0o755)
    monkeypatch.setattr(backend, "_dependency_manifest", lambda _: {
        "manifest_sha256": "0" * 64, "mathlib_revision": PINNED_MATHLIB_SHA})
    assert prove(target, project_root=tmp_path)["status"] == "LEAN_UNAVAILABLE"
    dummy.write_text(f'#!/bin/sh\nif [ "$3" = "--version" ]; then echo "Lean (version {backend.LEAN_VERSION})"; fi\nexit 0\n')
    assert prove(target, project_root=tmp_path)["reason"] == "LEAN_AXIOM_REPORT_MISSING"


@pytest.mark.parametrize("field", ["statement", "scope", "source", "axioms", "status", "derivation",
                                   "toolchain", "stdout", "attestation", "witness"])
def test_offline_replay_rejects_tampering_after_rehash(field):
    target = relation({"clique": 1, "chromatic": -1}).to_dict()
    original = prove(target, project_root="/nonexistent")
    damaged = deepcopy(original)
    if field == "statement":
        damaged["statement"]["bound"]["assumption"] = "CONNECTED"
    elif field == "source":
        damaged["generated"]["source"] += "-- changed"
    elif field == "status":
        damaged["status"] = "FORMALLY_VERIFIED"
    elif field == "axioms":
        damaged["kernel"].update(status="FORMALLY_VERIFIED", accepted=True, axioms=["sorryAx"])
    elif field == "derivation":
        damaged["derivation"]["directions"][0]["lemmas"][0]["coefficient"] = 2
    elif field == "toolchain":
        damaged["toolchain"] = "untrusted"
    elif field == "stdout":
        damaged["kernel"]["stdout"] = "altered"
    elif field == "attestation":
        damaged["kernel"]["offline_audit_is_execution_attestation"] = True
    elif field == "scope":
        damaged["scope"] = "FIXED_ORDER"
    elif field == "witness":
        damaged["counterexample"] = {"exact_order": 2, "labelled_edge_mask": 1}
    damaged["record_sha256"] = digest({k: v for k, v in damaged.items() if k != "record_sha256"})
    with pytest.raises(ValueError):
        audit(damaged)
