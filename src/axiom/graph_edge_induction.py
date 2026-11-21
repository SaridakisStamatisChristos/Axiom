"""A finite edge-deletion induction certificate for affine composition."""
from .graph_proof_search import LemmaSpec
from .graph_relations import _vector

EDGE_INDUCTION_VERSION = "axiom.graph_edge_induction.v1"
EDGE_INDUCTION_RULE = LemmaSpec(
    "edge_induction_order_le_edges_add_independence", "ALL",
    _vector((("n", 1), ("edges", -1), ("independence", -1))), 0,
)

# The helper quantifies over the graph so the induction hypothesis applies to
# the graph with one edge deleted, while the vertex type stays fixed.
EDGE_INDUCTION_PROOF = """\
  have bound (G : SimpleGraph (Fin n)) [DecidableRel G.Adj] :
      n ≤ edges G + independence G := by
    classical
    induction h : edges G using Nat.strong_induction_on generalizing G with
    | h m ih =>
      by_cases hz : G.edgeFinset = ∅
      · have hg := G.edgeFinset_eq_empty.mp hz
        subst G
        have hu : (⊥ : SimpleGraph (Fin n)).IsIndepSet (↑(Finset.univ : Finset (Fin n))) := by
          intro a _ b _ _
          simp
        have hc := hu.card_le_indepNum
        have hc' : n ≤ independence (⊥ : SimpleGraph (Fin n)) := by
          simpa [independence] using hc
        omega
      · obtain ⟨e, he⟩ := Finset.nonempty_iff_ne_empty.mpr hz
        revert he
        refine Sym2.inductionOn e ?_
        intro u v he
        let H := G.deleteEdges ({s(u, v)} : Set (Sym2 (Fin n)))
        have hEdges : H.edgeFinset = G.edgeFinset.erase s(u, v) := by
          ext e
          simp [H, SimpleGraph.edgeSet_deleteEdges, and_comm]
        have hstep : edges H + 1 = edges G := by
          unfold edges
          rw [hEdges, Finset.card_erase_of_mem he]
          have := Finset.card_pos.mpr ⟨_, he⟩
          omega
        have hIH := ih (edges H) (show edges H < m by omega) H rfl
        obtain ⟨S, hS⟩ := H.exists_isNIndepSet_indepNum
        have hI : G.IsIndepSet (↑(S.erase u)) := by
          intro a ha b hb hab habG
          have ha' := Finset.mem_erase.mp ha
          have hb' := Finset.mem_erase.mp hb
          apply hS.isIndepSet ha'.2 hb'.2 hab
          apply SimpleGraph.deleteEdges_adj.mpr
          refine ⟨habG, ?_⟩
          intro hs
          have hu : u ∈ s(a, b) := by
            rw [Set.mem_singleton_iff.mp hs]
            simp
          simp [ha'.1, hb'.1, Ne.symm] at hu
        have hIcard := hI.card_le_indepNum
        have hScard := hS.card_eq
        have hErase : S.card ≤ (S.erase u).card + 1 := by
          by_cases hm : u ∈ S
          · rw [Finset.card_erase_of_mem hm]
            have := Finset.card_pos.mpr ⟨_, hm⟩
            omega
          · rw [Finset.erase_eq_of_notMem hm]
            omega
        unfold independence at *
        omega
  have h := bound G
  omega"""
