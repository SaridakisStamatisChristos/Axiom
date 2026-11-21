"""Certified branch facts for the zero/positive order partition."""
from .graph_affine import VARIABLES
from .graph_proof_search import LemmaSpec
from .graph_relations import _vector
from .graph_universal_lean import _lemma_facts

ORDER_SPLIT_VERSION = "axiom.graph_order_split.v1"

# These are available only after Lean introduces the positive-order hypothesis.
# The bank is never extended with these facts outside the positive branch.
_POSITIVE_FACTS = {
    "order_positive": ({"n": -1}, -1, "have order_positive : 1 ≤ n := hn"),
    "order_degree_lt": (
        {"maximum_degree": 1, "n": -1}, -1,
        "have order_degree_lt : maximumDegree G < n := by\n"
        "  simpa [maximumDegree] using G.maxDegree_lt_card_verts",
    ),
    "order_clique_positive": (
        {"clique": -1}, -1,
        "have order_clique_positive : 1 ≤ clique G := by\n"
        "  exact Nat.pos_of_ne_zero G.cliqueNum_ne_zero_of_finite",
    ),
    "order_independence_positive": (
        {"independence": -1}, -1,
        "have order_independence_positive : 1 ≤ independence G := by\n"
        "  change 0 < G.indepNum\n"
        "  rw [← SimpleGraph.cliqueNum_compl]\n"
        "  exact Nat.pos_of_ne_zero Gᶜ.cliqueNum_ne_zero_of_finite",
    ),
}
POSITIVE_BANK = tuple(LemmaSpec(name, "ALL", _vector(weights.items()), rhs)
                      for name, (weights, rhs, _) in _POSITIVE_FACTS.items())

_EMPTY_FACTS = {
    "edges": "have z_edges : edges G = 0 := by\n"
             "  apply Nat.eq_zero_of_le_zero\n"
             "  simpa [edges] using G.card_edgeFinset_le_card_choose_two",
    "triangles": "have z_triangles : triangles G = 0 := by\n"
                 "  have h : G.cliqueFinset 3 = ∅ := by\n"
                 "    apply Finset.eq_empty_iff_forall_notMem.mpr\n"
                 "    intro s hs\n"
                 "    have hc := (SimpleGraph.mem_cliqueFinset_iff.mp hs).card_eq\n"
                 "    have hs0 : s = ∅ := Finset.eq_empty_iff_forall_notMem.mpr (fun v => Fin.elim0 v)\n"
                 "    simp [hs0] at hc\n"
                 "  simp [triangles, h]",
    "independence": "have z_independence : independence G = 0 := by\n"
                    "  rw [independence, ← SimpleGraph.cliqueNum_compl]\n"
                    "  simp",
    "clique": "have z_clique : clique G = 0 := by\n"
              "  simp [clique]",
    "chromatic": "have z_chromatic : chromatic G = 0 := by\n"
                 "  simp [chromatic]",
    "maximum_degree": "have z_degree : maximumDegree G = 0 := by\n"
                      "  apply Nat.eq_zero_of_le_zero\n"
                      "  exact G.maxDegree_le_of_forall_degree_le 0 (fun v => Fin.elim0 v)",
    "matching": "have z_matching : matching G = 0 := by\n"
                "  have hm := matching_le_edges G\n"
                "  omega",
    "components": "have z_components : components G = 0 := by\n"
                  "  have hc := components_le_order G\n"
                  "  omega",
}


def proof_body(claim, global_matches, local_names):
    """Render both branches of the original universally quantified goal."""
    zero = ["subst n"]
    if claim.bound.assumption == "CONNECTED":
        zero.extend(("rcases premise.nonempty with ⟨v⟩", "exact Fin.elim0 v"))
    else:
        symbols = {symbol for symbol, _ in claim.bound.terms}
        if "matching" in symbols:
            symbols.add("edges")
        zero.extend(_EMPTY_FACTS[symbol] for symbol in VARIABLES
                    if symbol != "n" and symbol in symbols)
        zero.append("omega")

    positive = ["have hn : 0 < n := Nat.pos_of_ne_zero hz",
                "let : Nonempty (Fin n) := ⟨⟨0, hn⟩⟩"]
    positive.extend(_POSITIVE_FACTS[name][2] for name in local_names)
    facts = _lemma_facts(global_matches)
    if facts:
        positive.append("\n".join(line[2:] for line in facts.splitlines()))
    positive.append("omega")
    return ("  by_cases hz : n = 0\n"
            + "\n".join("  · " + "\n    ".join("\n".join(branch).splitlines())
                        for branch in (zero, positive)))
