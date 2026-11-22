"""Freeze typed proof challenges from independent mathematical bounds."""
import argparse
from collections import Counter
import json
from pathlib import Path

from axiom.graph_relations import AffineRelation

ROOT = Path(__file__).resolve().parents[1]
# Each anchor defines a cluster, not five independent statistical observations.
# Secondary bounds are added with positive coefficients, preserving validity.
ANCHORS = (
    ("ALL", "matching_endpoints", {"matching": 2, "n": -1}, 0),
    ("ALL", "greedy_coloring", {"chromatic": 1, "maximum_degree": -1}, 1),
    ("ALL", "clique_triples", {"clique": 2, "triangles": -1}, 5),
    ("ALL", "clique_independent_intersection", {"clique": 1, "independence": 1, "n": -1}, 1),
    ("ALL", "component_palette", {"chromatic": 1, "components": 1, "n": -1}, 1),
    ("CONNECTED", "chromatic_core", {"chromatic": 2, "edges": -1, "n": 1}, 6),
    ("CONNECTED", "spanning_tree", {"n": 1, "edges": -1}, 1),
    ("CONNECTED", "independent_color_class", {"independence": 1, "chromatic": 1, "n": -1}, 1),
    ("CONNECTED", "nonadjacent_pair_coloring", {"chromatic": 2, "clique": -1, "n": -1}, 0),
    ("CONNECTED", "connected_degree_sum", {"n": 1, "maximum_degree": 1, "edges": -2}, 1),
    ("TRIANGLE_FREE", "neighborhood_deletion", {"chromatic": 1, "matching": -1}, 1),
    ("TRIANGLE_FREE", "independent_neighborhood", {"maximum_degree": 1, "independence": -1}, 0),
    ("TRIANGLE_FREE", "clique_exclusion", {"clique": 1}, 2),
    ("TRIANGLE_FREE", "vertex_cover_matching", {"independence": 1, "matching": 1, "n": -1}, 0),
    ("TRIANGLE_FREE", "triangle_count", {"triangles": 1}, 0),
    ("BIPARTITE", "konig", {"n": 1, "independence": -1, "matching": -1}, 0),
    ("BIPARTITE", "clique_coloring_equality", {"chromatic": 1, "clique": -1}, 0),
    ("BIPARTITE", "matching_contraction", {"matching": 1, "components": 1, "n": -1}, 0),
    ("BIPARTITE", "bipartition_size", {"n": 1, "independence": -2}, 0),
    ("BIPARTITE", "component_coloring", {"chromatic": 1, "components": -1}, 1),
)
SECONDARY = (
    ({"clique": 1, "n": -1}, 0),
    ({"independence": 1, "n": -1}, 0),
    ({"maximum_degree": 1, "edges": -1}, 0),
    ({"chromatic": 1, "n": -1}, 0),
    ({"clique": 1, "chromatic": -1}, 0),
    ({"matching": 1, "edges": -1}, 0),
    ({"n": 1, "independence": -1, "edges": -1}, 0),
    ({"components": 1, "n": -1}, 0),
    ({"clique": 1, "triangles": -1}, 2),
    ({"chromatic": 1, "maximum_degree": -1}, 1),
    ({"matching": 2, "n": -1}, 0),
    ({"independence": 1, "matching": 1, "n": -1}, 0),
    ({"clique": 1, "independence": 1, "n": -1}, 1),
    ({"clique": 1, "triangles": -1, "n": -1}, 0),
)


def direction(claim):
    return claim.bound.assumption, claim.bound.terms


def excluded_directions():
    stop = set()
    previous = ("targets", "heldout_graphs_v1", "retrieval_targets", "synthesis_targets",
                "order_split_targets", "edge_induction_targets", "proof_plan_targets", "proof_hint_targets")
    for name in previous:
        path = ROOT / "research/proof_engine" / f"{name}.json"
        rows = json.loads(path.read_text())
        if type(rows) is not list:
            continue
        for row in rows:
            if len(row) >= 4 and type(row[2]) is dict:
                stop.add(direction(AffineRelation.normalized(row[2], row[3], row[1])))
    for premise, _, terms, upper in ANCHORS:
        stop.add(direction(AffineRelation.normalized(terms, upper, premise)))
    return stop


def freeze():
    excluded = excluded_directions()
    cases = []
    for index, (premise, family, terms, rhs) in enumerate(ANCHORS):
        count = 0
        for offset in range(len(SECONDARY)):
            other, upper = SECONDARY[(index * 3 + offset) % len(SECONDARY)]
            scale = 1 + (count == 2)
            weights = Counter(terms)
            weights.update({name: scale * weight for name, weight in other.items()})
            weights = {name: weight for name, weight in weights.items() if weight}
            if len(weights) < 2 or len(weights) > 6:
                continue
            claim = AffineRelation.normalized(weights, rhs + scale * upper, premise)
            key = direction(claim)
            if key in excluded:
                continue
            excluded.add(key)
            count += 1
            cases.append({"id": f"P{len(cases) + 1:03d}", "family": family, "statement": claim.to_dict()})
            if count == 5:
                break
        if count != 5:
            raise ValueError(f"insufficient distinct directions in {family}")
    return {"schema": "axiom.graph_proof_coverage.v1", "cases": cases}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    suite = freeze()
    with args.output.open("x", encoding="utf-8") as file:
        json.dump(suite, file, indent=2, sort_keys=True)
        file.write("\n")
