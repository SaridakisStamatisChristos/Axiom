"""A versioned index of affine adapters for pinned Mathlib graph theorems."""
from dataclasses import asdict, dataclass

from .graph_claims import digest
from .graph_proof_search import LemmaSpec
from .graph_relations import AffineRelation, _vector
from .graph_universal_lean import PINNED_MATHLIB_SHA


@dataclass(frozen=True)
class MathlibAdapter:
    lemma: LemmaSpec
    declarations: tuple[str, ...]
    proof: str


def _adapter(name, premise, weights, rhs, declarations, proof):
    return MathlibAdapter(LemmaSpec("retrieved_" + name, premise, _vector(weights.items()), rhs),
                         declarations, proof)


# Each entry has a closed, checked translation to AXIOM's graph semantics.
# Goal statements, even when supplied via JSON, never contribute Lean code here.
_INDEX_V1 = (
    _adapter("clique_le_order", "ALL", {"clique": 1, "n": -1}, 0,
             ("SimpleGraph.cliqueNum_le_natCard",),
             "have h : clique G ≤ n := by\n"
             "    simpa [clique, Nat.card_eq_fintype_card] using G.cliqueNum_le_natCard\n"
             "  omega"),
    _adapter("independence_le_order", "ALL", {"independence": 1, "n": -1}, 0,
             ("SimpleGraph.cliqueNum_compl", "SimpleGraph.cliqueNum_le_natCard"),
             "have h : independence G ≤ n := by\n"
             "    simpa [independence, Nat.card_eq_fintype_card] using Gᶜ.cliqueNum_le_natCard\n"
             "  omega"),
    _adapter("chromatic_le_order", "ALL", {"chromatic": 1, "n": -1}, 0,
             ("SimpleGraph.chromaticNumber_le_card",),
             "have h : chromatic G ≤ n := by\n"
             "    simpa [chromatic] using ENat.toNat_le_toNat G.chromaticNumber_le_card "
             "(ENat.natCast_lt_top _).ne\n"
             "  omega"),
    _adapter("degree_le_edges", "ALL", {"maximum_degree": 1, "edges": -1}, 0,
             ("SimpleGraph.maxDegree_le_of_forall_degree_le", "SimpleGraph.degree_le_card_edgeFinset"),
             "have h : maximumDegree G ≤ edges G := by\n"
             "    exact G.maxDegree_le_of_forall_degree_le _ (fun v => G.degree_le_card_edgeFinset v)\n"
             "  omega"),
    _adapter("bipartite_chromatic_le_two", "BIPARTITE", {"chromatic": 1}, 2,
             ("SimpleGraph.chromaticNumber_le_two_iff_isBipartite",),
             "have h : chromatic G ≤ 2 := by\n"
             "    have hb := (G.chromaticNumber_le_two_iff_isBipartite).mpr premise\n"
             "    simpa [chromatic] using ENat.toNat_le_toNat hb "
             "(show (2 : ENat) ≠ ⊤ from by decide)\n"
             "  omega"),
)

INDEX_VERSION = "axiom.mathlib_affine_graph_index.v1"
INDEX_SHA256 = digest({
    "schema": INDEX_VERSION,
    "mathlib_revision": PINNED_MATHLIB_SHA,
    "entries": [{"lemma": asdict(a.lemma), "declarations": a.declarations, "proof": a.proof}
                for a in _INDEX_V1],
})
MAX_RETRIEVED_LEMMAS = 32


def retrieve(claim: AffineRelation, limit: int) -> tuple[MathlibAdapter, ...]:
    """Rank exact directions first, then signed overlaps and sparse supports."""
    targets = [_vector(side.terms) for side in claim.inequalities()]

    def rank(entry):
        vector = entry.lemma.vector
        shared = max(sum(x * y > 0 for x, y in zip(vector, target)) for target in targets)
        return (vector not in targets, -shared, sum(x != 0 for x in vector), entry.lemma.theorem)

    applicable = (entry for entry in _INDEX_V1
                  if entry.lemma.premise in ("ALL", claim.bound.assumption))
    return tuple(sorted(applicable, key=rank)[:limit])


def describe(entry):
    return {"adapter": entry.lemma.theorem, "premise": entry.lemma.premise,
            "mathlib_declarations": list(entry.declarations)}
