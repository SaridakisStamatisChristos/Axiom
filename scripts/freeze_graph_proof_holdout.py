"""Generate an outcome-blind proof holdout from independently justified anchors."""
import argparse
from collections import Counter
import json
from pathlib import Path
from random import Random

from axiom.graph_relations import AffineRelation
from freeze_graph_proof_coverage import ANCHORS as DEVELOPMENT_ANCHORS
from freeze_graph_proof_coverage import ROOT, SECONDARY, direction, excluded_directions

SEED = 112711
# See docs/graph_proof_holdout.md for the mathematical justification of each row.
ANCHORS = (
    ("ALL", "degree_order", {"maximum_degree": 1, "n": -1}, 0),
    ("ALL", "matching_vertex_cover_palette", {"chromatic": 1, "matching": -2}, 1),
    ("ALL", "components_independent_representatives", {"components": 1, "independence": -1}, 0),
    ("ALL", "single_independent_color_class", {"chromatic": 1, "independence": 1, "n": -1}, 1),
    ("ALL", "matching_edge_inclusion", {"matching": 1, "edges": -1}, 0),
    ("CONNECTED", "nonempty_order", {"n": -1}, -1),
    ("CONNECTED", "connected_degree_order", {"maximum_degree": 1, "n": -1}, -1),
    ("CONNECTED", "component_uniqueness", {"components": -1}, -1),
    ("CONNECTED", "color_order_edges", {"chromatic": 1, "edges": -1}, 1),
    ("CONNECTED", "connected_independence_order", {"independence": 1, "n": -1, "components": 1}, 1),
    ("TRIANGLE_FREE", "greedy_independent_neighborhood", {"chromatic": 1, "independence": -1}, 1),
    ("TRIANGLE_FREE", "clique_degree_or_neighborhood", {"clique": 1, "independence": -1}, 1),
    ("TRIANGLE_FREE", "triangle_nonnegativity", {"triangles": -1}, 0),
    ("TRIANGLE_FREE", "independent_neighborhood_order", {"maximum_degree": 1, "n": -1}, 0),
    ("TRIANGLE_FREE", "triangle_free_matching_palette", {"clique": 1, "matching": -1}, 1),
    ("BIPARTITE", "two_color_palette", {"chromatic": 1}, 2),
    ("BIPARTITE", "reverse_clique_palette", {"clique": 1, "chromatic": -1}, 0),
    ("BIPARTITE", "clique_order", {"clique": 1, "n": -1}, 0),
    ("BIPARTITE", "bipartite_matching_independent_side",
     {"matching": 1, "independence": -1}, 0),
    ("BIPARTITE", "component_independence", {"components": 1, "independence": -1}, 0),
)
# Preserve the secondary catalog and add elementary nonnegativity directions.
SECONDARIES = SECONDARY + tuple(
    ({name: -1}, 0) for name in ("chromatic", "clique", "components", "edges",
                                 "independence", "matching", "maximum_degree", "triangles")
)


def freeze():
    data = ROOT / "research/proof_engine"
    previous = json.loads((data / "proof_coverage_100_v1.json").read_bytes())
    excluded = excluded_directions() | {
        direction(AffineRelation.from_dict(case["statement"])) for case in previous["cases"]
    }
    excluded.update(direction(AffineRelation.normalized(terms, upper, scope))
                    for scope, _, terms, upper in (*DEVELOPMENT_ANCHORS, *ANCHORS))
    # The small historical competition file has a different row layout.
    regression = json.loads((ROOT / "research/autographforge/heldout-proof-v1.json").read_bytes())
    excluded.update(direction(AffineRelation.normalized(terms, upper, scope, relation))
                    for _, scope, terms, upper, relation, _ in regression)

    randomizer = Random(SEED)
    cases = []
    for scope, family, anchor, bound in ANCHORS:
        choices = [(terms, upper, scale) for terms, upper in SECONDARIES for scale in (1, 2)]
        randomizer.shuffle(choices)
        count = 0
        for terms, upper, scale in choices:
            weights = Counter(anchor)
            weights.update({name: scale * value for name, value in terms.items()})
            weights = {name: value for name, value in weights.items() if value}
            if not 2 <= len(weights) <= 6:
                continue
            claim = AffineRelation.normalized(weights, bound + scale * upper, scope)
            key = direction(claim)
            if key in excluded:
                continue
            excluded.add(key)
            count += 1
            cases.append({"id": f"H{len(cases) + 1:03d}", "family": family,
                          "statement": claim.to_dict()})
            if count == 5:
                break
        if count != 5:
            raise ValueError(f"insufficient distinct directions in {family}")
    return {"schema": "axiom.graph_proof_coverage.v1", "cases": cases}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    with args.output.open("x", encoding="utf-8") as file:
        json.dump(freeze(), file, indent=2, sort_keys=True)
        file.write("\n")
