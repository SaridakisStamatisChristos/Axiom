"""A versioned index of affine adapters for pinned Mathlib graph theorems."""
from dataclasses import asdict, dataclass

from .graph_bipartite_matching import BIPARTITE_MATCHING_PROOF
from .graph_affine import MAX_COEFFICIENT, VARIABLES
from .graph_claims import digest
from .graph_palette_bounds import INDEPENDENT_PALETTE, MATCHING_PALETTE
from .graph_component_coloring import COMPONENT_COLORING_PROOF
from .graph_decomposition_bounds import CONNECTED_CHROMATIC_EDGES_PROOF, TRIANGLE_FREE_MATCHING_PROOF, critical_edge_tangent
from .graph_matching_cardinality import MATCHING_CARDINALITY_PROOF
from .graph_proof_search import LemmaSpec
from .graph_relations import AffineRelation, _vector
from .graph_universal_lean import PINNED_MATHLIB_SHA, _lemma_facts


@dataclass(frozen=True)
class MathlibAdapter:
    lemma: LemmaSpec
    declarations: tuple[str, ...]
    proof: str
    imports: tuple[str, ...] = ()
    parents: tuple["MathlibAdapter", ...] = ()


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

_INDEX_V4 = _INDEX_V3 + (
    _adapter(
        "chromatic_add_components_le_order_add_one", "ALL",
        {"chromatic": 1, "components": 1, "n": -1}, 1,
        ("SimpleGraph.ConnectedComponent.sound", "Finset.card_image_of_injective",
         "Finset.card_add_card_compl", "SimpleGraph.Coloring.mk",
         "SimpleGraph.Colorable.chromaticNumber_le"),
        COMPONENT_COLORING_PROOF,
    ),
    _adapter(
        "connected_components_le_one", "CONNECTED", {"components": 1}, 1,
        ("SimpleGraph.Preconnected.subsingleton_connectedComponent", "Nat.card_eq_one_iff_unique"),
        """\
have h : components G = 1 := Nat.card_eq_one_iff_unique.mpr
    ⟨premise.preconnected.subsingleton_connectedComponent,
      Nonempty.map G.connectedComponentMk premise.nonempty⟩
  omega""",
    ),
)

_INDEX_V5 = _INDEX_V4 + (
    _adapter(
        "components_le_independence", "ALL", {"components": 1, "independence": -1}, 0,
        ("SimpleGraph.ConnectedComponent.sound", "Finset.card_image_of_injective",
         "SimpleGraph.IsIndepSet.card_le_indepNum"),
        """\
classical
  have surj : Function.Surjective G.connectedComponentMk := Quot.mk_surjective
  let rep : G.ConnectedComponent → Fin n := fun c => (surj c).choose
  have section_rep : Function.LeftInverse G.connectedComponentMk rep :=
    fun c => (surj c).choose_spec
  let reps : Finset (Fin n) := Finset.univ.image rep
  have hreps : reps.card = components G := by
    simp [reps, Finset.card_image_of_injective _ section_rep.injective,
      components, Nat.card_eq_fintype_card]
  have independent : G.IsIndepSet (↑reps : Set (Fin n)) := by
    intro u hu v hv hne adj
    obtain ⟨a, _, rfl⟩ := Finset.mem_image.mp (Finset.mem_coe.mp hu)
    obtain ⟨b, _, rfl⟩ := Finset.mem_image.mp (Finset.mem_coe.mp hv)
    have hc := SimpleGraph.ConnectedComponent.sound adj.reachable
    rw [section_rep a, section_rep b] at hc
    exact hne (congrArg rep hc)
  have h : components G ≤ independence G := hreps ▸ independent.card_le_indepNum
  omega""",
    ),
)

_INDEX_V6 = _INDEX_V5 + (
    _adapter(
        "twice_matching_le_order", "ALL", {"matching": 2, "n": -1}, 0,
        ("SimpleGraph.Subgraph.isMatching_iff_forall_degree",
         "SimpleGraph.sum_degrees_eq_twice_card_edges",
         "SimpleGraph.Subgraph.image_coe_edgeSet_coe",
         "Fintype.card_le_of_injective"),
        MATCHING_CARDINALITY_PROOF,
    ),
)

_INDEX_V7 = _INDEX_V6 + (
    _adapter(
        "clique_add_independence_le_order_add_one", "ALL",
        {"clique": 1, "independence": 1, "n": -1}, 1,
        ("SimpleGraph.exists_isNClique_cliqueNum", "SimpleGraph.exists_isNIndepSet_indepNum",
         "Finset.card_union_add_card_inter", "Finset.card_le_one_iff"),
        """\
classical
  obtain ⟨C, hC⟩ := G.exists_isNClique_cliqueNum
  obtain ⟨S, hS⟩ := G.exists_isNIndepSet_indepNum
  have intersection : (C ∩ S).card ≤ 1 := by
    apply Finset.card_le_one_iff.mpr
    intro a b ha hb
    by_contra hab
    have ha' := Finset.mem_inter.mp ha
    have hb' := Finset.mem_inter.mp hb
    exact hS.isIndepSet ha'.2 hb'.2 hab (hC.isClique ha'.1 hb'.1 hab)
  have union : (C ∪ S).card ≤ n := by
    simpa only [Fintype.card_fin] using Finset.card_le_univ (C ∪ S)
  have total := Finset.card_union_add_card_inter C S
  have clique_card := hC.card_eq
  have independent_card := hS.card_eq
  unfold clique independence
  omega""",
    ),
)

_INDEX_V8 = _INDEX_V7 + (
    _adapter(
        "twice_clique_le_triangles_add_five", "ALL", {"clique": 2, "triangles": -1}, 5,
        ("SimpleGraph.exists_isNClique_cliqueNum", "SimpleGraph.mem_cliqueFinset_iff",
         "Finset.card_powersetCard", "Nat.choose_succ_succ", "Nat.choose_le_choose"),
        """\
classical
  have choose_bound (k : Nat) : 2 * k ≤ k.choose 3 + 5 := by
    induction k with
    | zero => decide
    | succ k ih =>
      by_cases h : 3 ≤ k
      · have h2 : 2 ≤ k.choose 2 :=
          (show 2 ≤ (3 : Nat).choose 2 from by decide).trans (Nat.choose_le_choose 2 h)
        rw [Nat.choose_succ_succ k 2]
        change 2 * (k + 1) ≤ k.choose 2 + k.choose 3 + 5
        omega
      · have small : k = 0 ∨ k = 1 ∨ k = 2 := by omega
        rcases small with rfl | rfl | rfl <;> decide
  obtain ⟨s, hs⟩ := G.exists_isNClique_cliqueNum
  have hsubset : s.powersetCard 3 ⊆ G.cliqueFinset 3 := by
    intro t ht
    obtain ⟨hst, hcard⟩ := Finset.mem_powersetCard.mp ht
    exact SimpleGraph.mem_cliqueFinset_iff.mpr
      ⟨(hs.isClique.subset (by exact_mod_cast hst)), hcard⟩
  have hcount := Finset.card_le_card hsubset
  rw [Finset.card_powersetCard, hs.card_eq] at hcount
  have hfinal := choose_bound (G.cliqueNum)
  unfold clique triangles
  omega""",
    ),
    _adapter(
        "twice_chromatic_le_clique_add_order", "ALL", {"chromatic": 2, "clique": -1, "n": -1}, 0,
        ("SimpleGraph.chromaticNumber_top", "SimpleGraph.cliqueNum_top", "SimpleGraph.cliqueNum_induce_le",
         "SimpleGraph.colorable_chromaticNumber_of_fintype", "SimpleGraph.Coloring.mk"),
        """\
classical
  have aux (k : Nat) : ∀ (V : Type) [Fintype V] (H : SimpleGraph V),
      Fintype.card V = k → 2 * H.chromaticNumber.toNat ≤ H.cliqueNum + k := by
    induction k using Nat.strong_induction_on with
    | h k ih =>
      intro V inst H hk
      by_cases htop : H = ⊤
      · subst H
        simp [SimpleGraph.chromaticNumber_top, SimpleGraph.cliqueNum_top,
          Nat.card_eq_fintype_card, hk]
        omega
      · have hpair : ∃ a b : V, a ≠ b ∧ ¬ H.Adj a b := by
          by_contra! hall
          apply htop
          ext a b
          exact ⟨fun h => H.ne_of_adj h, fun h => hall a b h⟩
        obtain ⟨a, b, hab, hn⟩ := hpair
        let rest : Finset V := (Finset.univ.erase a).erase b
        let J := H.induce (rest : Set V)
        have hcard : rest.card + 2 = k := by
          have hb : b ∈ Finset.univ.erase a := Finset.mem_erase.mpr ⟨hab.symm, Finset.mem_univ _⟩
          have ha : a ∈ (Finset.univ : Finset V) := Finset.mem_univ _
          have h1 := Finset.card_erase_add_one hb
          have h2 := Finset.card_erase_add_one ha
          rw [Finset.card_univ, hk] at h2
          change ((Finset.univ.erase a).erase b).card + 2 = k
          omega
        have hrest : Fintype.card (rest : Set V) = rest.card := Fintype.card_coe rest
        have hj := ih rest.card (by omega) _ J hrest
        have hcl := H.cliqueNum_induce_le (rest : Set V)
        change J.cliqueNum ≤ H.cliqueNum at hcl
        let q := J.chromaticNumber.toNat
        obtain ⟨c⟩ : J.Colorable q := J.colorable_chromaticNumber_of_fintype
        let f (v : V) : Fin (q + 1) :=
          if hv : v ∈ rest then (c ⟨v, hv⟩).castSucc else Fin.last q
        have hc : H.Colorable (q + 1) := by
          refine ⟨SimpleGraph.Coloring.mk f ?_⟩
          intro u v huv
          by_cases hu : u ∈ rest <;> by_cases hv : v ∈ rest
          · simpa [f, hu, hv] using c.valid (show J.Adj ⟨u, hu⟩ ⟨v, hv⟩ from huv)
          · simp [f, hu, hv]
          · simpa [f, hu, hv] using (Fin.castSucc_ne_last (c ⟨v, hv⟩)).symm
          · have houtside (w : V) (hw : w ∉ rest) : w = a ∨ w = b := by
              by_contra! h
              exact hw (Finset.mem_erase.mpr ⟨h.2, Finset.mem_erase.mpr ⟨h.1, Finset.mem_univ _⟩⟩)
            rcases houtside u hu with rfl | rfl <;> rcases houtside v hv with rfl | rfl
            · exact (H.ne_of_adj huv rfl).elim
            · exact (hn huv).elim
            · exact (hn huv.symm).elim
            · exact (H.ne_of_adj huv rfl).elim
        have hb := ENat.toNat_le_toNat hc.chromaticNumber_le (ENat.natCast_ne_top _)
        simp only [ENat.toNat_natCast] at hb
        change 2 * q ≤ _ at hj
        omega
  have h := aux n (Fin n) G (Fintype.card_fin n)
  unfold chromatic clique
  omega""",
    ),
)

_INDEX_V9 = _INDEX_V8 + (
    _adapter(
        "triangle_free_chromatic_le_matching_add_one", "TRIANGLE_FREE",
        {"chromatic": 1, "matching": -1}, 1,
        ("SimpleGraph.CliqueFree.comap", "SimpleGraph.Subgraph.IsMatching.map",
         "SimpleGraph.Subgraph.IsMatching.sup", "SimpleGraph.Subgraph.IsMatching.subgraphOfAdj",
         "SimpleGraph.Coloring.mk"),
        TRIANGLE_FREE_MATCHING_PROOF,
    ),
    _adapter(
        "connected_twice_chromatic_le_edges_sub_order_add_six", "CONNECTED",
        {"chromatic": 2, "edges": -1, "n": 1}, 6,
        ("SimpleGraph.Coloring.mk", "SimpleGraph.sum_degrees_eq_twice_card_edges",
         "SimpleGraph.Connected.exists_isTree_le",
         "SimpleGraph.Connected.exists_isTree_le_of_le_of_isAcyclic",
         "SimpleGraph.IsTree.card_edgeFinset"),
        CONNECTED_CHROMATIC_EDGES_PROOF,
        imports=("Mathlib.Combinatorics.SimpleGraph.DegreeSum",),
    ),
)


def _combined_adapter(name, weights, rhs, *parents, premise="ALL"):
    facts = _lemma_facts((entry.lemma.theorem, entry.lemma.premise) for entry in parents)
    lemma = LemmaSpec("retrieved_" + name, premise, _vector(weights.items()), rhs)
    return MathlibAdapter(
        lemma, tuple(dict.fromkeys(declaration for entry in parents for declaration in entry.declarations)),
        facts.strip() + "\n  omega", parents=parents,
    )


_V9_BY_NAME = {entry.lemma.theorem: entry for entry in _INDEX_V9}
_INDEX_V11 = _INDEX_V9 + (
    _adapter("triangle_free_clique_le_two", "TRIANGLE_FREE", {"clique": 1}, 2,
             ("SimpleGraph.cliqueFinset_eq_empty_iff",), """\
have hz := SimpleGraph.cliqueFinset_eq_empty_iff.mpr premise
  have ht : triangles G = 0 := by simp [triangles, hz]
  have hc := clique_le_triangles_add_two G
  omega"""),
    _adapter("triangles_nonnegative", "ALL", {"triangles": -1}, 0, (), "omega"),
    _combined_adapter(
        "matching_add_components_le_order", {"matching": 1, "components": 1, "n": -1}, 0,
        _V9_BY_NAME["retrieved_matching_add_independence_le_order"],
        _V9_BY_NAME["retrieved_components_le_independence"],
    ),
)


_CONNECTED_UPPER = _V9_BY_NAME["retrieved_connected_components_le_one"]
_INDEX_V12 = _INDEX_V11 + (
    _adapter("connected_components_ge_one", "CONNECTED", {"components": -1}, -1,
             _CONNECTED_UPPER.declarations, _CONNECTED_UPPER.proof),
    _adapter("independent_palette", "ALL", {"chromatic": 1, "independence": 1, "n": -1}, 1,
             ("SimpleGraph.exists_isNIndepSet_indepNum", "SimpleGraph.Coloring.mk",
              "Finset.card_add_card_compl"), INDEPENDENT_PALETTE),
    _adapter("matching_palette", "ALL", {"chromatic": 1, "matching": -2}, 1,
             ("SimpleGraph.Subgraph.IsMatching.map", "SimpleGraph.Subgraph.IsMatching.sup",
              "SimpleGraph.Subgraph.IsMatching.subgraphOfAdj", "SimpleGraph.Coloring.mk"),
             MATCHING_PALETTE),
)


_INDEX_V13 = _INDEX_V12 + (
    _combined_adapter(
        "bipartite_matching_le_independence", {"matching": 1, "independence": -1}, 0,
        _V9_BY_NAME["retrieved_twice_matching_le_order"],
        _V9_BY_NAME["retrieved_bipartite_order_le_matching_add_independence"],
        premise="BIPARTITE",
    ),
    *(_adapter(f"{symbol}_nonnegative", "ALL", {symbol: -1}, 0, (), "omega")
      for symbol in ("components", "chromatic")),
)


_TANGENTS = tuple(
    _adapter(f"critical_{'connected' if connected else 'all'}_slope_{slope}",
             "CONNECTED" if connected else "ALL",
             {"chromatic": slope, "edges": -1, **({"n": 1} if connected else {})},
             (slope + int(connected)) * (slope + int(connected) + 1) // 2,
             _V9_BY_NAME["retrieved_connected_twice_chromatic_le_edges_sub_order_add_six"].declarations,
             critical_edge_tangent(slope, connected),
             imports=("Mathlib.Combinatorics.SimpleGraph.DegreeSum",))
    for connected in (False, True) for slope in range(2, MAX_COEFFICIENT + 1)
)


def _clique_tangent(parent):
    lemma = parent.lemma
    weights = dict(zip(VARIABLES, lemma.vector))
    weights["clique"] = weights.pop("chromatic")
    proof = _lemma_facts([(lemma.theorem, lemma.premise)]).strip() + "\n  have := clique_le_chromatic G\n  omega"
    return MathlibAdapter(LemmaSpec(lemma.theorem + "_clique", lemma.premise, _vector(weights.items()), lemma.rhs),
                          (*parent.declarations, "SimpleGraph.cliqueNum_le_chromaticNumber"), proof, parents=(parent,))


_INDEX_V14 = _INDEX_V13 + _TANGENTS + tuple(_clique_tangent(entry) for entry in _TANGENTS)

INDEX_VERSION = "axiom.mathlib_affine_graph_index.v1"
STRUCTURAL_INDEX = "axiom.mathlib_affine_graph_index.v2"
MATCHING_INDEX = "axiom.mathlib_affine_graph_index.v3"
COMPONENT_INDEX = "axiom.mathlib_affine_graph_index.v4"
COMPONENT_INDEPENDENCE_INDEX = "axiom.mathlib_affine_graph_index.v5"
MATCHING_CARDINALITY_INDEX = "axiom.mathlib_affine_graph_index.v6"
CLIQUE_INDEPENDENCE_INDEX = "axiom.mathlib_affine_graph_index.v7"
CLIQUE_BOUNDS_INDEX = "axiom.mathlib_affine_graph_index.v8"
DECOMPOSITION_INDEX = "axiom.mathlib_affine_graph_index.v9"
SCHEDULED_INDEX = "axiom.mathlib_affine_graph_index.v10"
CERTIFICATE_INDEX = "axiom.mathlib_affine_graph_index.v11"
PALETTE_INDEX = "axiom.mathlib_affine_graph_index.v12"
CARDINALITY_INDEX = "axiom.mathlib_affine_graph_index.v13"
ROUNDING_BUDGET_DIVISOR = 5
EXTREMAL_INDEX = "axiom.mathlib_affine_graph_index.v14"

_INDEXES = {INDEX_VERSION: _INDEX_V1, STRUCTURAL_INDEX: _INDEX_V2, MATCHING_INDEX: _INDEX_V3,
            COMPONENT_INDEX: _INDEX_V4, COMPONENT_INDEPENDENCE_INDEX: _INDEX_V5,
            MATCHING_CARDINALITY_INDEX: _INDEX_V6, CLIQUE_INDEPENDENCE_INDEX: _INDEX_V7,
            CLIQUE_BOUNDS_INDEX: _INDEX_V8, DECOMPOSITION_INDEX: _INDEX_V9, SCHEDULED_INDEX: _INDEX_V9,
            CERTIFICATE_INDEX: _INDEX_V11, PALETTE_INDEX: _INDEX_V12, CARDINALITY_INDEX: _INDEX_V13, EXTREMAL_INDEX: _INDEX_V14}
_MATCHING_CARDINALITY_ADAPTER = "retrieved_twice_matching_le_order"
_MATCHING_CARDINALITY_POLICY = "offer_cardinality_adapter_for_matching_coefficient_at_least_two"
_CLIQUE_INDEPENDENCE_ADAPTER = "retrieved_clique_add_independence_le_order_add_one"
_CLIQUE_INDEPENDENCE_POLICY = "offer_joint_bound_for_positive_clique_and_independence"
_CLIQUE_TRIANGLE_ADAPTER = "retrieved_twice_clique_le_triangles_add_five"
_CLIQUE_TRIANGLE_POLICY = "offer_clique_triangle_bound_for_positive_clique_and_negative_triangles"
_COLOR_CLIQUE_ADAPTER = "retrieved_twice_chromatic_le_clique_add_order"
_COLOR_CLIQUE_POLICY = "offer_chromatic_bound_for_positive_chromatic_negative_clique_and_order"
_COLOR_MATCHING_ADAPTER = "retrieved_triangle_free_chromatic_le_matching_add_one"
_COLOR_MATCHING_POLICY = "offer_triangle_free_matching_bound_for_positive_chromatic"
_COLOR_EDGES_ADAPTER = "retrieved_connected_twice_chromatic_le_edges_sub_order_add_six"
_COLOR_EDGES_POLICY = "offer_connected_coloring_bound_for_positive_chromatic_or_clique_and_negative_edges"
INDEX_DIGESTS = {version: digest({
    "schema": version,
    "mathlib_revision": PINNED_MATHLIB_SHA,
    "entries": [{"lemma": asdict(a.lemma), "declarations": a.declarations, "proof": a.proof,
                 **({"imports": a.imports} if a.imports else {}),
                 **({"parents": [parent.lemma.theorem for parent in a.parents]} if a.parents else {})}
                for a in entries],
    **({"selection": _MATCHING_CARDINALITY_POLICY} if version == MATCHING_CARDINALITY_INDEX else {}),
    **({"selection": [_MATCHING_CARDINALITY_POLICY, _CLIQUE_INDEPENDENCE_POLICY]}
       if version == CLIQUE_INDEPENDENCE_INDEX else {}),
    **({"selection": [_MATCHING_CARDINALITY_POLICY, _CLIQUE_INDEPENDENCE_POLICY,
                       _CLIQUE_TRIANGLE_POLICY, _COLOR_CLIQUE_POLICY]}
       if version == CLIQUE_BOUNDS_INDEX else {}),
    **({"selection": [_MATCHING_CARDINALITY_POLICY, _CLIQUE_INDEPENDENCE_POLICY,
                       _CLIQUE_TRIANGLE_POLICY, _COLOR_CLIQUE_POLICY, _COLOR_MATCHING_POLICY,
                       _COLOR_EDGES_POLICY]}
       if version in (DECOMPOSITION_INDEX, SCHEDULED_INDEX) else {}),
    **({"composition": "bounded_integer_rounding"} if version == DECOMPOSITION_INDEX else {}),
    **({"composition": {"schedule": "direct_then_rounding_then_plans", "index_leaves": True,
                        "rounding_budget_divisor": ROUNDING_BUDGET_DIVISOR,
                        "reserve_plan_slots": True}} if version == SCHEDULED_INDEX else {}),
    **({"composition": {"schedule": "v10_then_inventory_certificate_then_plans",
                        "baseline_index": SCHEDULED_INDEX,
                        "rounding_budget_divisor": ROUNDING_BUDGET_DIVISOR}}
       if version in (CERTIFICATE_INDEX, PALETTE_INDEX, CARDINALITY_INDEX, EXTREMAL_INDEX) else {}),
}) for version, entries in _INDEXES.items()}
INDEX_SHA256 = INDEX_DIGESTS[INDEX_VERSION]
MAX_RETRIEVED_LEMMAS = 32


def retrieve(claim: AffineRelation, limit: int, *, index=INDEX_VERSION) -> tuple[MathlibAdapter, ...]:
    """Rank exact directions first, then signed overlaps and sparse supports."""
    if index in (CERTIFICATE_INDEX, PALETTE_INDEX, CARDINALITY_INDEX, EXTREMAL_INDEX):
        index = SCHEDULED_INDEX
    directions = claim.inequalities()
    targets = [_vector(side.terms) for side in directions]
    weights = [dict(side.terms) for side in directions]
    needs_cardinality = any(row.get("matching", 0) >= 2 for row in weights)
    needs_joint_bound = any(row.get("clique", 0) > 0 and row.get("independence", 0) > 0 for row in weights)
    needs_clique_triangle_bound = any(row.get("clique", 0) > 0 and row.get("triangles", 0) < 0
                                      for row in weights)
    needs_color_clique_bound = any(row.get("chromatic", 0) > 0 and row.get("clique", 0) < 0
                                  and row.get("n", 0) < 0 for row in weights)
    needs_color_matching_bound = any(row.get("chromatic", 0) > 0 for row in weights)
    needs_color_edges_bound = any(row.get("edges", 0) < 0
                                  and (row.get("chromatic", 0) > 0 or row.get("clique", 0) > 0)
                                  for row in weights)

    def rank(entry):
        vector = entry.lemma.vector
        shared = max(sum(x * y > 0 for x, y in zip(vector, target)) for target in targets)
        return (vector not in targets, -shared, sum(x != 0 for x in vector), entry.lemma.theorem)

    applicable = (entry for entry in _INDEXES[index]
                  if entry.lemma.premise in ("ALL", claim.bound.assumption)
                  and (entry.lemma.theorem != _MATCHING_CARDINALITY_ADAPTER or needs_cardinality)
                  and (entry.lemma.theorem != _CLIQUE_INDEPENDENCE_ADAPTER or needs_joint_bound)
                  and (entry.lemma.theorem != _CLIQUE_TRIANGLE_ADAPTER or needs_clique_triangle_bound)
                  and (entry.lemma.theorem != _COLOR_CLIQUE_ADAPTER or needs_color_clique_bound)
                  and (entry.lemma.theorem != _COLOR_MATCHING_ADAPTER or needs_color_matching_bound)
                  and (entry.lemma.theorem != _COLOR_EDGES_ADAPTER or needs_color_edges_bound))
    return tuple(sorted(applicable, key=rank)[:limit])


def indexed_facts(index):
    """Return the full pinned inventory, without top-k retrieval."""
    return _INDEXES[index]


def describe(entry):
    return {"adapter": entry.lemma.theorem, "premise": entry.lemma.premise,
            "mathlib_declarations": list(entry.declarations),
            **({"mathlib_imports": list(entry.imports)} if entry.imports else {}),
            **({"adapter_dependencies": [parent.lemma.theorem for parent in entry.parents]}
               if entry.parents else {})}
