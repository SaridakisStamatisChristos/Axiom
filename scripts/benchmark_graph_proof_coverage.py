"""Run the frozen AXIOM proof-coverage and AutoGraphForge CPU-tactic benchmark."""
import argparse
import ast
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from hashlib import sha256
from importlib.resources import files
import json
from pathlib import Path
import platform
import random
import subprocess
from time import perf_counter

from axiom.graph_affine import check_conjecture
from axiom.graph_affine_lean_n3 import run_affine_kernel
from axiom.graph_campaign import _discovery_properties
from axiom.graph_checker import reference_properties
from axiom.graph_lemma_retrieval import CLIQUE_INDEPENDENCE_INDEX, DECOMPOSITION_INDEX
from axiom.graph_model import edge_positions
from axiom.graph_proof import audit, prove
from axiom.graph_proof_search import SearchLimits
from axiom.graph_relations import AffineRelation
from axiom.graph_universal_lean import _PREMISES, _render_terms

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "research/proof_engine"
MANIFEST = DATA / "proof_coverage_100_v1.json"
PROTOCOL = DATA / "proof_coverage_protocol_v1.json"
INDEXES = {"v7": CLIQUE_INDEPENDENCE_INDEX, "v9": DECOMPOSITION_INDEX}
COLUMNS = {"n": "order", "edges": "size", "clique": "clique_number",
           "independence": "independence_number", "maximum_degree": "maximum_degree",
           "chromatic": "chromatic_number", "matching": "matching_number",
           "triangles": "number_of_triangles", "components": "number_connected_components"}
CLASSES = {"CONNECTED": "connected", "TRIANGLE_FREE": "triangle_free", "BIPARTITE": "bipartite"}
SUCCESS = "FORMALLY_VERIFIED"
COMPETITOR = "autographforge-cpu-tactics"


def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


def read(path):
    return json.loads(path.read_bytes())


def write(path, payload):
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temp.replace(path)


def frozen_suite(protocol):
    raw = MANIFEST.read_bytes()
    if sha256(raw).hexdigest() != protocol["manifest_sha256"]:
        raise ValueError("proof-coverage manifest differs from the frozen protocol")
    suite = json.loads(raw)
    cases = suite["cases"]
    claims = [AffineRelation.from_dict(case["statement"]) for case in cases]
    directions = {(claim.bound.assumption, claim.bound.terms) for claim in claims}
    sizes = Counter(case["family"] for case in cases)
    if (suite["schema"] != "axiom.graph_proof_coverage.v1"
            or len(cases) != len({case["id"] for case in cases}) or len(cases) != len(directions)
            or len(cases) != protocol["cases"] or len(sizes) != protocol["families"]
            or set(sizes.values()) != {5}
            or Counter(claim.bound.assumption for claim in claims) != dict.fromkeys(
                ("ALL", "BIPARTITE", "CONNECTED", "TRIANGLE_FREE"), 25)):
        raise ValueError("malformed proof-coverage suite")
    return cases


def literal_assignment(tree, name):
    for node in tree:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            target = node.targets[0]
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            target = node.target
        else:
            continue
        if target.id == name:
            return ast.literal_eval(node.value)
    raise ValueError(f"pinned AutoGraphForge declaration missing: {name}")


def competitor_config(checkout, protocol):
    if git(checkout, "rev-parse", "HEAD") != protocol["autographforge_commit"]:
        raise ValueError("AutoGraphForge checkout differs from the frozen protocol")
    exporter = "pipeline/lean_export.py"
    prover = "pipeline/theorem_prover.py"
    files_by_path = {path: git(checkout, "show", f"HEAD:{path}") for path in (exporter, prover)}
    for path, frozen_text in files_by_path.items():
        if (checkout / path).read_text().strip() != frozen_text:
            raise ValueError(f"modified AutoGraphForge input: {path}")
    proof_tree = ast.parse(files_by_path[prover])
    tactic_class, = (node for node in proof_tree.body
                    if isinstance(node, ast.ClassDef) and node.name == "LeanSubprocessProver")
    tactics = literal_assignment(tactic_class.body, "_SIMPLE_TACTICS")
    if any(not tactic.isidentifier() for tactic in tactics):
        raise ValueError("unexpected upstream tactic syntax")
    export_tree = ast.parse(files_by_path[exporter]).body
    return {"tactics": tactics, "invariants": list(literal_assignment(export_tree, "SUPPORTED")),
            "classes": list(literal_assignment(export_tree, "CLASS_PREDICATES")),
            "source_sha256": {path: sha256(data.encode()).hexdigest() for path, data in files_by_path.items()}}


def native_vocabulary(claim, config):
    missing = {COLUMNS[symbol] for symbol, _ in claim.bound.terms} - set(config["invariants"])
    scope = CLASSES.get(claim.bound.assumption)
    if scope is not None and scope not in config["classes"]:
        missing.add(scope)
    return sorted(missing)


def tactic_source(claim, tactics):
    raw = files("axiom").joinpath("lean", "GraphUniversal.lean").read_text(encoding="utf-8")
    definitions, separator, _ = raw.partition("\nomit [DecidableRel G.Adj]")
    if not separator or "\ntheorem " in definitions or "\naxiom " in definitions:
        raise ValueError("unexpected invariant-only preamble")
    bound = claim.bound
    name = "cpu_tactic_target"
    alternatives = "\n".join(f"  | ({tactic} <;> done)" for tactic in tactics)
    lean = (
        definitions + "\nend\n\n"
        f"theorem {name} (n : Nat) (G : SimpleGraph (Fin n)) [DecidableRel G.Adj]"
        f"{_PREMISES[bound.assumption]} :\n"
        f"    {_render_terms(bound.terms)} ≤ ({bound.upper} : Int) := by\n"
        f"  first\n{alternatives}\n"
        f"#print axioms {name}\nend AxiomGraphUniversal\n"
    )
    return {"source": lean, "source_sha256": sha256(lean.encode()).hexdigest(),
            "theorem": f"AxiomGraphUniversal.{name}"}


def check_oracles(cases, order_limit):
    claims = [(case["id"], AffineRelation.from_dict(case["statement"]).bound) for case in cases]
    masks = 0
    coverage = Counter({case["id"]: 0 for case in cases})
    for order in range(order_limit + 1):
        for mask in range(1 << len(edge_positions(order))):
            masks += 1
            one = reference_properties(order, mask)
            two = _discovery_properties(order, mask)
            for identity, bound in claims:
                applicable, valid, value = check_conjecture(bound, one)
                if (applicable, valid, value) != check_conjecture(bound, two):
                    raise ValueError(f"independent oracles disagree on {identity} at {order}/{mask}")
                if applicable:
                    if not valid:
                        raise ValueError(f"false input {identity} at {order}/{mask}: {value}")
                    coverage[identity] += 1
    return {"orders": list(range(order_limit + 1)), "labelled_graphs": masks,
            "applicable_by_case": dict(coverage)}


def run_case(case, protocol, competitor, output):
    claim = AffineRelation.from_dict(case["statement"])
    budget = protocol["budget"]
    missing = native_vocabulary(claim, competitor)
    report = {"case": case, "missing_native_vocabulary": missing, "lanes": {}}
    order = protocol["lanes"]
    offset = (int(case["id"][1:]) - 1) % len(order)
    for lane in order[offset:] + order[:offset]:
        start = perf_counter()
        if lane == COMPETITOR:
            source = tactic_source(claim, competitor["tactics"])
            attempt = run_affine_kernel(source, ROOT, budget["timeout"], SUCCESS,
                                        expected_mathlib_revision=protocol["mathlib"], retain_logs=True)
        else:
            attempt = prove(
                case["statement"], project_root=ROOT, timeout=budget["timeout"],
                limits=SearchLimits(budget["max_lemmas"], budget["max_coefficient"], budget["max_nodes"]),
                witness_order=budget["witness_order"], retrieval_index=INDEXES[lane],
                retrieval_limit=budget["retrieval_limit"], synthesis_limit=budget["synthesis_limit"],
                split_order=True, induct_edges=True, plan_limit=budget["plan_limit"],
            )
        elapsed = perf_counter() - start
        if lane != COMPETITOR:
            audit(attempt)
            if attempt["status"] == "COUNTEREXAMPLE":
                raise ValueError(f"counterexample to frozen input {case['id']}")
        record = attempt if lane == COMPETITOR else attempt.get("kernel") or {}
        if (attempt["status"] == SUCCESS and not record.get("lean_kernel_executed")
                or attempt["status"] in {"LEAN_UNAVAILABLE", "CONFIGURATION_MISSING"}
                or record.get("status") in {"VERSION_MISMATCH", "DEPENDENCY_MANIFEST_MISSING",
                                            "MATHLIB_REVISION_MISMATCH", "VERSION_CHECK_FAILED",
                                            "CHECKER_IO_ERROR"}):
            raise ValueError(f"invalid kernel environment for {case['id']} in {lane}")
        report["lanes"][lane] = {"wall_seconds": round(elapsed, 6), "attempt": attempt}
    write(output / f"{case['id']}.json", report)
    return case["id"], [report["lanes"][lane]["attempt"]["status"] for lane in order]


def proved(row, lane):
    return row["lanes"][lane]["attempt"]["status"] == SUCCESS


def paired(rows, baseline, contender, protocol):
    clusters = defaultdict(list)
    changes = Counter()
    for row in rows:
        delta = int(proved(row, contender)) - int(proved(row, baseline))
        changes[delta] += 1
        clusters[row["case"]["family"]].append(delta)
    if not rows:
        return None
    # Resample whole anchor families. On a vocabulary subset, resampled groups
    # can contribute different case counts, so recompute the denominator.
    values = [(sum(group), len(group)) for group in clusters.values()]
    randomizer = random.Random(protocol["bootstrap_seed"])
    reps = []
    for _ in range(protocol["bootstrap_replicates"]):
        sampled = randomizer.choices(values, k=len(values))
        reps.append(100 * sum(total for total, _ in sampled) / sum(count for _, count in sampled))
    reps.sort()
    return {"baseline": baseline, "contender": contender,
            "case_count": len(rows), "family_count": len(values),
            "wins": changes[1], "losses": changes[-1],
            "delta_points": 100 * (changes[1] - changes[-1]) / len(rows),
            "paired_family_bootstrap_95_points": [reps[int(0.025 * len(reps))],
                                                 reps[int(0.975 * len(reps))]]}


def summarize(rows, protocol):
    def totals(cohort):
        return {lane: dict(Counter(row["lanes"][lane]["attempt"]["status"] for row in cohort))
                for lane in protocol["lanes"]}

    common = [row for row in rows if not row["missing_native_vocabulary"]]
    pairs = (("v7", "v9"), (COMPETITOR, "v9"))
    by_scope = defaultdict(list)
    for row in rows:
        by_scope[row["case"]["statement"]["bound"]["assumption"]].append(row)
    delta = paired(rows, "v7", "v9", protocol)["delta_points"]
    return {"all": totals(rows), "native_vocabulary_overlap": totals(common),
            "by_scope": {scope: totals(group) for scope, group in by_scope.items()},
            "paired_all": [paired(rows, a, b, protocol) for a, b in pairs],
            "paired_native_vocabulary_overlap": [paired(common, a, b, protocol) for a, b in pairs],
            "coverage_gate_passed": delta >= protocol["coverage_gate_points"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--autographforge", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--workers", type=int, choices=range(1, 9), default=4)
    args = parser.parse_args()
    protocol = read(PROTOCOL)
    cases = frozen_suite(protocol)
    if git(ROOT, "diff", "--name-only", protocol["axiom_commit"], "--",
           "src", "lake-manifest.json", "lakefile.toml", "lean-toolchain"):
        raise ValueError("AXIOM engine or dependencies differ from the frozen protocol")
    competitor = competitor_config(args.autographforge.resolve(), protocol)
    args.output.mkdir()
    output = args.output.resolve()
    write(output / "run.json", {"protocol": protocol, "competitor": competitor,
                                "benchmark_commit": git(ROOT, "rev-parse", "HEAD"),
                                "platform": platform.platform(), "python": platform.python_version(),
                                "workers": args.workers})
    write(output / "truth-screen.json", check_oracles(cases, protocol["budget"]["witness_order"]))
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(run_case, case, protocol, competitor, output) for case in cases]
        for future in as_completed(futures):
            identity, statuses = future.result()
            print(identity, *statuses, flush=True)
    summary = summarize([read(output / f"{case['id']}.json") for case in cases], protocol)
    write(output / "summary.json", summary)
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
