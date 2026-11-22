"""Check native export equivalence and one source-matched proof outside the scored run."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import re
import sys
from types import SimpleNamespace

from benchmark_graph_proof_coverage import (
    CLASSES, COLUMNS, INDEXES, PROTOCOL, ROOT, SUCCESS, AffineRelation,
    _PREMISES, _render_terms, audit, competitor_config, files, frozen_suite,
    git, native_vocabulary, prove, read, run_affine_kernel, sha256, write,
)

UPSTREAM_DEFS = "lean_project/LeanProject/GraphInvariants.lean"
UPSTREAM_PROOF = "results/verified_proofs/oprover-32b_61f2701ba25e.lean"


def definitions(root):
    source = git(root, "show", f"HEAD:{UPSTREAM_DEFS}")
    names = ("order", "size", "IsTriangleFreeClass", "IsBipartiteClass", "IsConnectedClass")
    definitions = []
    for name in names:
        pattern = rf"(?m)^(?:noncomputable )?def {name} [^\n]*(?:\n +[^\n]+)*"
        declaration, = re.findall(pattern, source)
        definitions.append(declaration)
    return ("namespace SimpleGraph\nvariable {V : Type*} [Fintype V] [DecidableEq V]\n"
            + "\n".join(definitions) + "\nend SimpleGraph\n")


def kernel(source, name, protocol):
    return run_affine_kernel(
        {"source": source, "source_sha256": sha256(source.encode()).hexdigest(), "theorem": name},
        ROOT, protocol["budget"]["timeout"], SUCCESS,
        expected_mathlib_revision=protocol["mathlib"], retain_logs=True,
    )


def check_native(case, protocol, competitor, native_defs, output, exporter, linear):
    claim = AffineRelation.from_dict(case["statement"])
    bound = claim.bound
    comparison = " + ".join(f"({weight} * {COLUMNS[symbol]})" for symbol, weight in bound.terms)
    comparison += f" <= {bound.upper}"
    antecedent = CLASSES.get(bound.assumption)
    if antecedent:
        expression = f"{antecedent} ⇒ {comparison}"
        native = exporter.render_conditioned(SimpleNamespace(pretty=lambda: expression),
                                             list(COLUMNS.values()) + list(CLASSES.values()))
        if native is None:
            raise ValueError(f"native export rejected {case['id']}")
        head, tail = native.split("\n  : ", 1)
        native_goal = tail.removesuffix(" :=\nsorry")
        native_header = head.split("theorem CEGIS_1 ", 1)[1]
        predicate = f"G.{exporter.CLASS_PREDICATES[antecedent]}"
    else:
        native_goal = linear.render_comparison(comparison, exporter.SUPPORTED)
        native_header = exporter._HEADER_BINDERS
        predicate = None
    if native_goal is None:
        raise ValueError(f"native normalizer rejected {case['id']}")

    raw = files("axiom").joinpath("lean", "GraphUniversal.lean").read_text(encoding="utf-8")
    left, right = raw.split("\nnamespace AxiomGraphUniversal\n", 1)
    axiom_defs = right.split("\nomit [DecidableRel G.Adj]", 1)[0]
    shared = left + native_defs + "\nopen SimpleGraph\n"
    header = "theorem native_tactic_target " + native_header + f" : {native_goal} := by\n"
    native_src = shared + header + "  first\n" + "\n".join(
        f"  | ({tactic} <;> done)" for tactic in competitor["tactics"]
    ) + "\n#print axioms native_tactic_target\n"
    native_result = kernel(native_src, "native_tactic_target", protocol)

    typed_goal = f"{_render_terms(bound.terms)} ≤ ({bound.upper} : Int)"
    compact = "SimpleGraph.order, SimpleGraph.size, Fintype.card_fin, edges, independence, clique, maximumDegree"
    if predicate:
        typed_predicate = _PREMISES[bound.assumption].strip().removeprefix("(premise : ").removesuffix(")")
        typed_goal = f"{typed_predicate} → {typed_goal}"
        native_goal = f"{predicate} → {native_goal}"
        if bound.assumption == "BIPARTITE":
            simplify = ("SimpleGraph.IsBipartiteClass, ← SimpleGraph.chromaticNumber_le_iff_colorable, "
                        "SimpleGraph.chromaticNumber_le_two_iff_isBipartite, " + compact)
        else:
            simplify = f"{exporter.CLASS_PREDICATES[antecedent]}, {compact}"
        tactic = f"  simp only [{simplify}]\n  constructor <;> intro h hp <;> have := h hp <;> omega\n"
    else:
        tactic = f"  simp only [{compact}]\n  omega\n"
    equiv_source = (
        shared + "\nnamespace AxiomGraphUniversal\n" + axiom_defs + "\nend\n"
        "theorem native_equivalent (n : Nat) (G : SimpleGraph (Fin n)) [DecidableRel G.Adj] :\n"
        f"    ({native_goal}) ↔ ({typed_goal}) := by\n" + tactic
        + "#print axioms native_equivalent\nend AxiomGraphUniversal\n"
    )
    equivalent = kernel(equiv_source, "AxiomGraphUniversal.native_equivalent", protocol)
    write(output / f"{case['id']}.json", {"case": case, "native_cpu": native_result, "equivalence": equivalent})
    if equivalent["status"] != SUCCESS:
        raise ValueError(equivalent.get("stdout") or equivalent)
    return case["id"], native_result["status"]


def source_matched(root, protocol, native_defs, output):
    source = git(root, "show", f"HEAD:{UPSTREAM_PROOF}")
    _, sep, proof = source.partition("\nset_option maxHeartbeats ")
    if not sep or "theorem omega_le_order" not in proof or "sorry" in proof:
        raise ValueError("unexpected pinned external proof artifact")
    prefix = ("import Mathlib.Combinatorics.SimpleGraph.Acyclic\n"
              "import Mathlib.Combinatorics.SimpleGraph.Bipartite\n"
              "import Mathlib.Data.Real.Basic\n"
              "import Mathlib.Tactic.Linarith\nimport Mathlib.Tactic.NormNum\n")
    native = kernel(prefix + native_defs + sep + proof + "\n#print axioms omega_le_order\n",
                    "omega_le_order", protocol)
    claim = AffineRelation.normalized({"clique": 1, "n": -1}, 0)
    axiom = prove(claim.to_dict(), project_root=ROOT, timeout=protocol["budget"]["timeout"],
                  retrieval_limit=5, retrieval_index=INDEXES["v9"])
    audit(axiom)
    # Keep the upstream artifact external and record the hash and kernel evidence.
    native.pop("source")
    write(output / "source-transfer.json", {
        "path": UPSTREAM_PROOF, "upstream_file_sha256": sha256(source.encode()).hexdigest(),
        "upstream_commit": protocol["autographforge_commit"], "autographforge": native, "axiom": axiom,
    })
    print(f"clique ≤ order: {native['status']} upstream, {axiom['status']} AXIOM")
    if native["status"] != SUCCESS or axiom["status"] != SUCCESS:
        raise ValueError(native.get("stdout") or native)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--autographforge", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    root = args.autographforge.resolve()
    protocol = read(PROTOCOL)
    competitor = competitor_config(root, protocol)
    native_defs = definitions(root)
    sys.path.insert(0, str(root))
    from pipeline import lean_export, linear_form

    args.output.mkdir()
    source_matched(root, protocol, native_defs, args.output)
    subset = [case for case in frozen_suite(protocol)
              if not native_vocabulary(AffineRelation.from_dict(case["statement"]), competitor)]
    with ThreadPoolExecutor(max_workers=2) as pool:
        statuses = dict(pool.map(
            lambda case: check_native(case, protocol, competitor, native_defs, args.output, lean_export, linear_form),
            subset,
        ))
    write(args.output / "summary.json", statuses)
    print(statuses)


if __name__ == "__main__":
    main()
