import Mathlib.Combinatorics.SimpleGraph.Acyclic
import Mathlib.Combinatorics.SimpleGraph.Bipartite
import Mathlib.Combinatorics.SimpleGraph.Matching

namespace AxiomGraphUniversal

open SimpleGraph Finset

noncomputable section

variable {n : Nat} (G : SimpleGraph (Fin n)) [DecidableRel G.Adj]

def edges : Nat := G.edgeFinset.card
def triangles : Nat := (G.cliqueFinset 3).card
def independence : Nat := G.indepNum
def clique : Nat := G.cliqueNum
def chromatic : Nat := G.chromaticNumber.toNat
def maximumDegree : Nat := G.maxDegree
def matching : Nat := sSup {k : Nat | ∃ M : G.Subgraph, M.IsMatching ∧ M.edgeSet.ncard = k}
def components : Nat := Nat.card G.ConnectedComponent

omit [DecidableRel G.Adj] in
theorem neighborhood_independent (h : G.CliqueFree 3) (v : Fin n) :
    G.IsIndepSet (G.neighborSet v) := by
  intro a ha b hb hab e
  apply h {v, a, b}
  have hxa : v ≠ a := (G.ne_of_adj ha)
  have hxb : v ≠ b := (G.ne_of_adj hb)
  refine ⟨?_, by simp [hxa, hxb, hab]⟩
  intro x hx y hy hxy
  simp only [Finset.mem_coe, mem_insert, mem_singleton] at hx hy
  rcases hx with rfl | rfl | rfl <;> rcases hy with rfl | rfl | rfl
  all_goals first | contradiction | exact ha | exact hb | exact ha.symm |
    exact hb.symm | exact e | exact e.symm

omit [DecidableRel G.Adj] in
theorem clique_le_chromatic : clique G ≤ chromatic G := by
  unfold clique chromatic
  simpa using ENat.toNat_le_toNat G.cliqueNum_le_chromaticNumber (G.chromaticNumber_le_card.trans_lt (ENat.natCast_lt_top _)).ne

theorem connected_edge_bound (h : G.Connected) : n ≤ edges G + 1 := by
  simpa [edges, Nat.card_eq_fintype_card, SimpleGraph.edgeFinset_card] using
    h.card_vert_le_card_edgeSet_add_one

theorem connected_component_edge_bound (h : G.Connected) : n ≤ edges G + components G := by
  have hcard : components G = 1 := Nat.card_eq_one_iff_unique.mpr
    ⟨h.preconnected.subsingleton_connectedComponent, Nonempty.map G.connectedComponentMk h.nonempty⟩
  simpa only [hcard] using connected_edge_bound G h

theorem neighborhood_degree_le_independence (h : G.CliqueFree 3) (v : Fin n) :
    G.degree v ≤ independence G := by
  change (G.neighborFinset v).card ≤ G.indepNum
  apply IsIndepSet.card_le_indepNum
  simpa using neighborhood_independent G h v

theorem triangle_free_degree_bound (h : G.CliqueFree 3) : maximumDegree G ≤ independence G :=
  G.maxDegree_le_of_forall_degree_le _ (neighborhood_degree_le_independence G h)

theorem matching_le_edges : matching G ≤ edges G := by
  classical
  unfold matching
  apply csSup_le'
  rintro k ⟨M, _, rfl⟩
  rw [edges, SimpleGraph.edgeFinset_card, Set.fintypeCard_eq_ncard]
  exact Set.ncard_le_ncard M.edgeSet_subset

theorem components_le_order : components G ≤ n := by
  simpa [components, Nat.card_eq_fintype_card] using
    (Nat.card_le_card_of_surjective G.connectedComponentMk Quot.mk_surjective)

theorem clique_le_triangles_add_two : clique G ≤ triangles G + 2 := by
  classical
  obtain ⟨s, hs⟩ := G.exists_isNClique_cliqueNum
  have hcard := hs.card_eq
  by_cases hsmall : s.card ≤ 2
  · unfold clique
    omega
  obtain ⟨a, ha⟩ := Finset.card_pos.mp (show 0 < s.card by omega)
  have hp : 0 < (s.erase a).card := by
    rw [Finset.card_erase_of_mem ha]
    omega
  obtain ⟨b, hb'⟩ := Finset.card_pos.mp hp
  have hb := Finset.mem_of_mem_erase hb'
  have hba := Finset.ne_of_mem_erase hb'
  have hinj : ((s.erase a).erase b).card ≤ (G.cliqueFinset 3).card := by
    apply Finset.card_le_card_of_injOn (fun x => {a, b, x})
    · intro x hx
      have hxb := Finset.ne_of_mem_erase hx
      have hxa := Finset.ne_of_mem_erase (Finset.mem_of_mem_erase hx)
      have hxs := Finset.mem_of_mem_erase (Finset.mem_of_mem_erase hx)
      have hsub : ({a, b, x} : Finset (Fin n)) ⊆ s := by
        intro y hy
        simp only [mem_insert, mem_singleton] at hy
        rcases hy with rfl | rfl | rfl <;> assumption
      refine SimpleGraph.mem_cliqueFinset_iff.mpr ⟨?_, by simp [hba.symm, hxa, hxb, Ne.symm]⟩
      intro u hu v hv huv
      exact hs.isClique (hsub hu) (hsub hv) huv
    · intro x hx y hy hxy
      change ({a, b, x} : Finset (Fin n)) = {a, b, y} at hxy
      have hx' : x ∈ ({a, b, y} : Finset (Fin n)) := by rw [← hxy]; simp
      simp only [mem_insert, mem_singleton] at hx'
      exact hx'.resolve_left (Finset.ne_of_mem_erase (Finset.mem_of_mem_erase hx))
        |>.resolve_left (Finset.ne_of_mem_erase hx)
  rw [Finset.card_erase_of_mem hb', Finset.card_erase_of_mem ha] at hinj
  unfold clique triangles
  omega

end

end AxiomGraphUniversal
