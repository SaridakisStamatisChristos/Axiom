"""Additional graph inequalities with self-contained mathematical justifications."""

# Each row applies to finite simple undirected graphs. The proof text is part
# of the immutable novelty manifest so historical evidence pins the premises.
STRUCTURAL_FACTS = (
    (
        "spanning_forest_edge_bound", "ALL",
        {"n": 1, "edges": -1, "components": -1}, 0,
        "Take a spanning tree of each connected component. Their union has n-c edges, "
        "all in the original graph. The empty union covers the empty graph.",
    ),
    (
        "chromatic_independent_palette_bound", "ALL",
        {"chromatic": 1, "independence": 1, "n": -1}, 1,
        "Give a maximum independent set one common color and every vertex outside it a fresh "
        "color. This uses at most n-alpha+1 colors, including for the empty graph.",
    ),
    (
        "connected_chromatic_cycle_rank_bound", "CONNECTED",
        {"chromatic": 1, "n": 1, "edges": -1}, 3,
        "Start with a two-coloring of a spanning tree, which has n-1 edges. Add the other "
        "m-n+1 edges one at a time. For each new edge whose endpoints share a color, "
        "recolor one endpoint with a fresh color. Each step needs at most one extra color.",
    ),
    (
        "maximum_degree_component_bound", "ALL",
        {"maximum_degree": 1, "components": 1, "n": -1}, 0,
        "On a nonempty graph, the component of a maximum-degree vertex contains that vertex "
        "and all its neighbors. Each other component contributes at least one additional "
        "vertex. All terms are zero on the empty graph.",
    ),
    (
        "maximum_matching_unmatched_independent", "ALL",
        {"n": 1, "matching": -2, "independence": -1}, 0,
        "The vertices left unmatched by a maximum matching are independent. An edge "
        "between two such vertices would extend the matching, contradicting maximality.",
    ),
    (
        "connected_component_lower_bound", "CONNECTED",
        {"components": -1}, -1,
        "A connected graph has a nonempty vertex set and exactly one connected component.",
    ),
    (
        "connected_order_lower_bound", "CONNECTED",
        {"n": -1}, -1,
        "The connected premise requires a nonempty vertex set.",
    ),
)
