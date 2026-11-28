"""Reconstruct the extremal transfer panels, excluding previously scored directions."""
from collections import Counter
import json
from math import comb

from freeze_graph_proof_coverage import AffineRelation, ROOT, SECONDARY, direction, excluded_directions

DATA = ROOT / "research/proof_engine"


def panels():
    seen = excluded_directions()
    for name in ("proof_coverage_100_v1", "proof_holdout_100_v1", "proof_holdout_100_v2"):
        for row in json.loads((DATA / f"{name}.json").read_text())["cases"]:
            seen.add(direction(AffineRelation.from_dict(row["statement"])))
    cases = []
    prefix = "F"

    def add(family, scope, weights, rhs):
        claim = AffineRelation.normalized(dict(weights), rhs, scope)
        key = direction(claim)
        if key in seen:
            return False
        seen.add(key)
        cases.append({"id": f"{prefix}{len(cases)+1:03}", "family": family, "statement": claim.to_dict()})
        return True

    def composites(family, scope, anchor, rhs):
        start = len(cases)
        for other, upper in (({}, 0), *SECONDARY):
            weights = Counter(anchor)
            weights.update(other)
            add(family, scope, {k: v for k, v in weights.items() if v}, rhs + upper)
            if len(cases) == start + 5:
                return
        raise ValueError(f"insufficient directions for {family}")

    for connected in (False, True):
        for symbol in ("chromatic", "clique"):
            family = symbol + ("_cycle_rank" if connected else "_edge_growth")
            for t in range(2, 9):
                weights = {symbol: t, "edges": -1}
                if connected:
                    weights["n"] = 1
                center = t + int(connected)
                add(family, "CONNECTED" if connected else "ALL", weights, center*(center+1)//2)
    composites("spanning_forest", "ALL", {"n": 1, "components": -1, "edges": -1}, 0)
    composites("unmatched_independence", "ALL", {"n": 1, "matching": -2, "independence": -1}, 0)
    composites("degree_component_order", "ALL", {"maximum_degree": 1, "components": 1, "n": -1}, 0)
    composites("bipartite_neighborhood", "BIPARTITE", {"maximum_degree": 1, "independence": -1}, 0)
    yield "family_transfer_v1", cases
    cases = []
    prefix = "B"
    for t in range(2, 9):
        add("clique_triangle_growth", "ALL", {"clique": t, "triangles": -1},
            max(t*w-comb(w, 3) for w in range(t+3)))
        add("star_clique_edges", "ALL", {"clique": t, "maximum_degree": 1, "edges": -1}, t*(t+3)//2)
        add("clique_forest_excess", "ALL", {"clique": t, "n": 1, "components": -1, "edges": -1}, t*(t+3)//2)
        add("mixed_palette", "ALL", {"chromatic": t-1, "clique": 1, "edges": -1}, t*(t+1)//2)
    composites("star_matching_union", "ALL", {"maximum_degree": 1, "matching": 1, "edges": -1}, 1)
    composites("clique_matching_endpoints", "ALL", {"clique": 1, "matching": -2}, 1)
    yield "extremal_blind_v1", cases


if __name__ == "__main__":
    for name, rows in panels():
        payload = {"schema": "axiom.graph_family_transfer.v1", "cases": rows}
        (DATA / f"{name}.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
