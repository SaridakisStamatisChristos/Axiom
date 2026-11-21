"""A versioned index of affine adapters for pinned Mathlib graph theorems."""
from dataclasses import asdict, dataclass

from .graph_bipartite_matching import BIPARTITE_MATCHING_PROOF
from .graph_claims import digest
from .graph_proof_search import LemmaSpec
from .graph_relations import AffineRelation, _vector
from .graph_universal_lean import PINNED_MATHLIB_SHA


@dataclass(frozen=True)
class MathlibAdapter:
    lemma: LemmaSpec
    declarations: tuple[str, ...]
    proof: str
    imports: tuple[str, ...] = ()


def _adapter(name, premise, weights, rhs, declarations, proof, *, imports=()):
    return MathlibAdapter(LemmaSpec("retrieved_" + name, premise, _vector(weights.items()), rhs),
                         declarations, proof, imports)


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

_INDEX_V2 = _INDEX_V1 + (
    _adapter("chromatic_le_degree_add_one", "ALL", {"chromatic": 1, "maximum_degree": -1}, 1,
             ("SimpleGraph.degree_le_maxDegree", "SimpleGraph.mem_neighborFinset",
              "Finset.exists_mem_notMem_of_card_lt_card", "SimpleGraph.Coloring.mk",
              "SimpleGraph.Colorable.chromaticNumber_le"), """\
classical
  have partial_coloring (s : Finset (Fin n)) :
      ∃ f : Fin n → Fin (maximumDegree G + 1),
        ∀ ⦃a b⦄, a ∈ s → b ∈ s → G.Adj a b → f a ≠ f b := by
    induction s using Finset.induction_on with
    | empty => exact ⟨fun _ => 0, by simp⟩
    | @insert v s hv ih =>
      obtain ⟨f, hf⟩ := ih
      let used := (s.filter (G.Adj v)).image f
      have hn : s.filter (G.Adj v) ⊆ G.neighborFinset v := by
        intro u hu
        exact (G.mem_neighborFinset v u).mpr (Finset.mem_filter.mp hu).2
      have hcard : used.card ≤ maximumDegree G :=
        Finset.card_image_le.trans ((Finset.card_le_card hn).trans (G.degree_le_maxDegree v))
      obtain ⟨k, _, hk⟩ := Finset.exists_mem_notMem_of_card_lt_card
        (t := Finset.univ) (s := used) (by simpa using Nat.lt_succ_of_le hcard)
      let g := Function.update f v k
      have different (u : Fin n) (hu : u ∈ s) (hvu : G.Adj v u) : k ≠ f u := by
        intro h
        apply hk
        exact Finset.mem_image.mpr ⟨u, Finset.mem_filter.mpr ⟨hu, hvu⟩, h.symm⟩
      have old_vertex (u : Fin n) (hu : u ∈ s) : u ≠ v := fun h => hv (h ▸ hu)
      refine ⟨g, ?_⟩
      intro a b ha hb hab
      rcases Finset.mem_insert.mp ha with rfl | has
      · have hbv := (G.ne_of_adj hab).symm
        have hbs := (Finset.mem_insert.mp hb).resolve_left hbv
        simpa [g, hbv] using different b hbs hab
      · rcases Finset.mem_insert.mp hb with rfl | hbs
        · simpa [g, old_vertex a has] using (different a has hab.symm).symm
        · simpa [g, old_vertex a has, old_vertex b hbs] using hf has hbs hab
  obtain ⟨f, hf⟩ := partial_coloring Finset.univ
  have hc : G.Colorable (maximumDegree G + 1) :=
    ⟨SimpleGraph.Coloring.mk f (fun hab => hf (Finset.mem_univ _) (Finset.mem_univ _) hab)⟩
  have hc' : G.chromaticNumber ≤ ((maximumDegree G + 1 : Nat) : ENat) := hc.chromaticNumber_le
  have h := ENat.toNat_le_toNat hc' (ENat.natCast_lt_top _).ne
  have h' : chromatic G ≤ maximumDegree G + 1 := by simpa only [chromatic, ENat.toNat_natCast] using h
  omega"""),
    _adapter("bipartite_chromatic_le_clique", "BIPARTITE", {"chromatic": 1, "clique": -1}, 0,
             ("SimpleGraph.chromaticNumber_eq_two_iff", "SimpleGraph.chromaticNumber_bot",
              "SimpleGraph.chromaticNumber_eq_zero_of_isEmpty", "SimpleGraph.cliqueNum_bot",
              "SimpleGraph.eq_bot_iff_forall_not_adj", "SimpleGraph.isClique_pair",
              "SimpleGraph.IsClique.card_le_cliqueNum"), """\
have bound : chromatic G ≤ clique G := by
    classical
    by_cases hV : Nonempty (Fin n)
    · let : Nonempty (Fin n) := hV
      by_cases hG : G = ⊥
      · subst G
        simp [chromatic, clique, SimpleGraph.chromaticNumber_bot, SimpleGraph.cliqueNum_bot]
      · have hC := SimpleGraph.chromaticNumber_eq_two_iff.mpr ⟨premise, hG⟩
        have hA : ∃ u v, G.Adj u v := by
          simpa [SimpleGraph.eq_bot_iff_forall_not_adj] using hG
        obtain ⟨u, v, huv⟩ := hA
        have hc : G.IsClique (↑({u, v} : Finset (Fin n))) := by
          simpa using SimpleGraph.isClique_pair.mpr (fun _ => huv)
        have h2 := hc.card_le_cliqueNum
        simp [G.ne_of_adj huv] at h2
        simpa [chromatic, clique, hC] using h2
    · let : IsEmpty (Fin n) := not_nonempty_iff.mp hV
      simp [chromatic]
  omega"""),
    _adapter("bipartite_triangles_zero", "BIPARTITE", {"triangles": 1}, 0,
             ("SimpleGraph.chromaticNumber_le_two_iff_isBipartite",
              "SimpleGraph.cliqueFree_of_chromaticNumber_lt", "SimpleGraph.cliqueFinset_eq_empty_iff"),
             """\
have hc : G.chromaticNumber ≤ 2 := SimpleGraph.chromaticNumber_le_two_iff_isBipartite.mpr premise
  have hf : G.CliqueFree 3 :=
    G.cliqueFree_of_chromaticNumber_lt (hc.trans_lt (by decide))
  have hz := SimpleGraph.cliqueFinset_eq_empty_iff.mpr hf
  simp [triangles, hz]"""),
    _adapter("triangle_free_triangles_zero", "TRIANGLE_FREE", {"triangles": 1}, 0,
             ("SimpleGraph.cliqueFinset_eq_empty_iff",), """\
have hz := SimpleGraph.cliqueFinset_eq_empty_iff.mpr premise
  simp [triangles, hz]"""),
    _adapter("matching_add_independence_le_order", "ALL", {"matching": 1, "independence": 1, "n": -1}, 0,
             ("SimpleGraph.exists_isNIndepSet_indepNum", "SimpleGraph.Subgraph.IsMatching.toEdge_eq_of_adj",
              "SimpleGraph.Subgraph.IsMatching.toEdge_eq_toEdge_of_adj",
              "Nat.card_le_card_of_surjective", "Nat.card_le_card_of_injective",
              "Finset.card_add_card_compl"), """\
classical
  obtain ⟨S, hS⟩ := G.exists_isNIndepSet_indepNum
  have hm : matching G ≤ (Sᶜ : Finset (Fin n)).card := by
    unfold matching
    apply csSup_le'
    rintro k ⟨M, hM, rfl⟩
    -- The vertices of the matching outside S still meet every matching edge.
    let A := {v : M.verts // (v : Fin n) ∉ S}
    let f : A → M.edgeSet := fun v => hM.toEdge v.1
    have hf : Function.Surjective f := by
      rintro ⟨⟨u, v⟩, huv⟩
      change M.Adj u v at huv
      by_cases hu : u ∈ S
      · have hv : v ∉ S := fun h => hS.isIndepSet hu h
          (G.ne_of_adj (M.adj_sub huv)) (M.adj_sub huv)
        refine ⟨⟨⟨v, huv.snd_mem⟩, hv⟩, ?_⟩
        exact (hM.toEdge_eq_toEdge_of_adj huv).symm.trans (hM.toEdge_eq_of_adj huv)
      · exact ⟨⟨⟨u, huv.fst_mem⟩, hu⟩, hM.toEdge_eq_of_adj huv⟩
    let g : A → ↥(Sᶜ : Finset (Fin n)) := fun v => ⟨v.1.1, Finset.mem_compl.mpr v.2⟩
    have hg : Function.Injective g := by
      intro a b hab
      apply Subtype.ext
      apply Subtype.ext
      exact congrArg (fun v : ↥(Sᶜ : Finset (Fin n)) => v.val) hab
    change Nat.card M.edgeSet ≤ (Sᶜ : Finset (Fin n)).card
    rw [← Fintype.card_coe (Sᶜ : Finset (Fin n)), ← Nat.card_eq_fintype_card]
    exact (Nat.card_le_card_of_surjective f hf).trans (Nat.card_le_card_of_injective g hg)
  have hsum := S.card_add_card_compl
  have hc := hS.card_eq
  simp only [Fintype.card_fin] at hsum
  unfold independence
  omega"""),
)

_INDEX_V3 = _INDEX_V2 + (
    _adapter(
        "bipartite_order_le_matching_add_independence", "BIPARTITE",
        {"n": 1, "matching": -1, "independence": -1}, 0,
        ("Finset.all_card_le_biUnion_card_iff_exists_injective",
         "SimpleGraph.exists_isNIndepSet_indepNum",
         "SimpleGraph.Subgraph.IsMatching.exists_of_disjoint_sets_of_equiv",
         "SimpleGraph.Subgraph.isMatching_iff_forall_degree",
         "SimpleGraph.sum_degrees_eq_twice_card_edges"),
        BIPARTITE_MATCHING_PROOF, imports=("Mathlib.Combinatorics.Hall.Basic",),
    ),
)

INDEX_VERSION = "axiom.mathlib_affine_graph_index.v1"
STRUCTURAL_INDEX = "axiom.mathlib_affine_graph_index.v2"
MATCHING_INDEX = "axiom.mathlib_affine_graph_index.v3"
_INDEXES = {INDEX_VERSION: _INDEX_V1, STRUCTURAL_INDEX: _INDEX_V2, MATCHING_INDEX: _INDEX_V3}
INDEX_DIGESTS = {version: digest({
    "schema": version,
    "mathlib_revision": PINNED_MATHLIB_SHA,
    "entries": [{"lemma": asdict(a.lemma), "declarations": a.declarations, "proof": a.proof,
                 **({"imports": a.imports} if a.imports else {})} for a in entries],
}) for version, entries in _INDEXES.items()}
INDEX_SHA256 = INDEX_DIGESTS[INDEX_VERSION]
MAX_RETRIEVED_LEMMAS = 32


def retrieve(claim: AffineRelation, limit: int, *, index=INDEX_VERSION) -> tuple[MathlibAdapter, ...]:
    """Rank exact directions first, then signed overlaps and sparse supports."""
    targets = [_vector(side.terms) for side in claim.inequalities()]

    def rank(entry):
        vector = entry.lemma.vector
        shared = max(sum(x * y > 0 for x, y in zip(vector, target)) for target in targets)
        return (vector not in targets, -shared, sum(x != 0 for x in vector), entry.lemma.theorem)

    applicable = (entry for entry in _INDEXES[index]
                  if entry.lemma.premise in ("ALL", claim.bound.assumption))
    return tuple(sorted(applicable, key=rank)[:limit])


def describe(entry):
    return {"adapter": entry.lemma.theorem, "premise": entry.lemma.premise,
            "mathlib_declarations": list(entry.declarations),
            **({"mathlib_imports": list(entry.imports)} if entry.imports else {})}
