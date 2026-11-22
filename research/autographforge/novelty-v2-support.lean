/- Append this file to GraphUniversal.lean to check the structural bounds. -/

namespace AxiomGraphUniversal

open SimpleGraph Finset

theorem novelty_chromatic_independence {n : Nat} (G : SimpleGraph (Fin n)) :
    chromatic G + independence G ≤ n + 1 := by
  classical
  obtain ⟨S, hS⟩ := G.exists_isNIndepSet_indepNum
  let f (v : Fin n) : Option (↥(Sᶜ : Finset (Fin n))) :=
    if h : v ∈ S then none else some ⟨v, Finset.mem_compl.mpr h⟩
  let C : G.Coloring (Option (↥(Sᶜ : Finset (Fin n)))) := Coloring.mk f (by
    intro v w hvw heq
    by_cases hv : v ∈ S <;> by_cases hw : w ∈ S
    · exact hS.isIndepSet hv hw (G.ne_of_adj hvw) hvw
    · simp [f, hv, hw] at heq
    · simp [f, hv, hw] at heq
    · exact G.ne_of_adj hvw (by simpa [f, hv, hw] using heq))
  have hb := ENat.toNat_le_toNat C.colorable.chromaticNumber_le (ENat.natCast_lt_top _).ne
  have hchi : chromatic G ≤ (Sᶜ : Finset (Fin n)).card + 1 := by
    simpa only [chromatic, ENat.toNat_natCast, Fintype.card_option, Fintype.card_coe] using hb
  have hs := S.card_add_card_compl
  have ha := hS.card_eq
  simp only [Fintype.card_fin] at hs
  unfold independence
  omega

theorem novelty_recolor_edge {n k : Nat} {H : SimpleGraph (Fin n)}
    {u v : Fin n} (hc : H.Colorable k) : (H ⊔ edge u v).Colorable (k + 1) := by
  classical
  obtain ⟨C⟩ := hc
  let f (w : Fin n) : Option (Fin k) := if w = u then none else some (C w)
  let c : (H ⊔ edge u v).Coloring (Option (Fin k)) := Coloring.mk f (by
    intro a b hab heq
    by_cases ha : a = u <;> by_cases hb : b = u
    · exact (H ⊔ edge u v).ne_of_adj hab (ha.trans hb.symm)
    · simp [f, ha, hb] at heq
    · simp [f, ha, hb] at heq
    · rcases hab with hH | he
      · exact C.valid hH (by simpa [f, ha, hb] using heq)
      · simp [SimpleGraph.edge_adj, ha, hb] at he)
  simpa using c.colorable


theorem novelty_chromatic_cycle_rank {n : Nat} (G : SimpleGraph (Fin n))
    [DecidableRel G.Adj] (h : G.Connected) : chromatic G + n ≤ edges G + 3 := by
  classical
  obtain ⟨T, hTG, hT⟩ := h.exists_isTree_le
  let cnt (K : SimpleGraph (Fin n)) := Nat.card K.edgeSet
  have card_eq (K : SimpleGraph (Fin n)) [DecidableRel K.Adj] : cnt K = edges K := by
    rw [edges, edgeFinset_card]
    exact Nat.card_eq_fintype_card
  have ht : cnt T + 1 = n := by rw [card_eq]; simpa [edges] using hT.card_edgeFinset
  have extend (K : SimpleGraph (Fin n)) (hTK : T ≤ K) :
      K.Colorable (2 + (cnt K - cnt T)) := by
    induction hk : cnt K using Nat.strong_induction_on generalizing K with
    | h m ih =>
      by_cases heq : K = T
      · subst K
        simpa [← hk] using hT.colorable_two
      · have hd : (K.edgeFinset \ T.edgeFinset).Nonempty := by
          by_contra hn
          have hs := Finset.sdiff_eq_empty_iff_subset.mp
            (Finset.not_nonempty_iff_eq_empty.mp hn)
          apply heq (le_antisymm ?_ hTK)
          intro x y hxy
          have hm : s(x,y) ∈ K.edgeFinset := by simpa using hxy
          simpa using hs hm
        obtain ⟨e, he⟩ := hd
        revert he
        refine Sym2.inductionOn e ?_
        intro a b he
        have heK := (Finset.mem_sdiff.mp he).1
        have heT := (Finset.mem_sdiff.mp he).2
        have hab : a ≠ b := K.ne_of_adj (by simpa using heK)
        let H := K.deleteEdges ({s(a,b)} : Set (Sym2 (Fin n)))
        have hTH : T ≤ H := by
          intro x y hxy
          refine SimpleGraph.deleteEdges_adj.mpr ⟨hTK hxy, ?_⟩
          intro hmem
          apply heT
          rw [← Set.mem_singleton_iff.mp hmem]
          simpa using hxy
        have hstep : edges H + 1 = edges K := by
          have hEdges : H.edgeFinset = K.edgeFinset.erase s(a,b) := by
            ext e
            simp [H, SimpleGraph.edgeSet_deleteEdges, and_comm]
          have hp := Finset.card_pos.mpr ⟨_, heK⟩
          unfold edges
          rw [hEdges, Finset.card_erase_of_mem heK]
          omega
        have hcount : cnt H + 1 = cnt K := by rw [card_eq H, card_eq K]; exact hstep
        have hh := ih (cnt H) (show cnt H < m by omega) H hTH rfl
        have hGrow : H ⊔ edge a b = K := by
          apply edgeSet_injective
          rw [edgeSet_sup, edgeSet_edge_of_ne hab]
          have habK : s(a,b) ∈ K.edgeSet := by simpa using heK
          ext e
          by_cases he : e = s(a,b)
          · subst e
            simp [habK]
          · simp [H, edgeSet_deleteEdges, he]
        have hn : cnt T ≤ cnt H := by
          rw [card_eq T, card_eq H]
          exact Finset.card_le_card (edgeFinset_mono hTH)
        have hcolors : 2 + (cnt H - cnt T) + 1 = 2 + (m - cnt T) := by omega
        simpa only [hGrow, hcolors] using (novelty_recolor_edge (u := a) (v := b) hh)
  have hc := (extend G hTG).chromaticNumber_le
  have hb := ENat.toNat_le_toNat hc (ENat.natCast_lt_top _).ne
  unfold chromatic
  simp only [ENat.toNat_natCast] at hb
  have hle : cnt T ≤ cnt G := by
    rw [card_eq T, card_eq G]
    exact Finset.card_le_card (edgeFinset_mono hTG)
  have hcnt := card_eq G
  omega

#print axioms novelty_chromatic_independence
#print axioms novelty_chromatic_cycle_rank


theorem novelty_spanning_forest_bound {n : Nat} (G : SimpleGraph (Fin n))
    [DecidableRel G.Adj] : n ≤ edges G + components G := by
  classical
  let F (c : G.ConnectedComponent) := c.toSimpleGraph.spanningCoe.edgeFinset
  have vertexDisjoint : (↑(Finset.univ : Finset G.ConnectedComponent) : Set G.ConnectedComponent).PairwiseDisjoint
      (fun c => c.supp.toFinset) := by
    intro c _ d _ h
    exact Set.disjoint_toFinset.mpr (pairwise_disjoint_supp_connectedComponent G h)
  have vertexUnion : (Finset.univ : Finset G.ConnectedComponent).biUnion
      (fun c => c.supp.toFinset) = (Finset.univ : Finset (Fin n)) := by
    ext v
    simp only [Finset.mem_biUnion, Finset.mem_univ, true_and, Set.mem_toFinset, iff_true]
    exact ⟨G.connectedComponentMk v, by simp [ConnectedComponent.mem_supp_iff]⟩
  have vertexCount : (∑ c : G.ConnectedComponent, c.supp.toFinset.card) = n := by
    rw [← Finset.card_biUnion vertexDisjoint, vertexUnion]
    simp
  have edgeDisjoint : (↑(Finset.univ : Finset G.ConnectedComponent) : Set G.ConnectedComponent).PairwiseDisjoint F := by
    intro c _ d _ hne
    apply Finset.disjoint_left.mpr
    intro e
    refine Sym2.inductionOn e ?_
    intro u v h1 h2
    have hc : u ∈ c.supp := (c.adj_spanningCoe_toSimpleGraph.mp (mem_edgeFinset.mp h1)).1
    have hd : u ∈ d.supp := (d.adj_spanningCoe_toSimpleGraph.mp (mem_edgeFinset.mp h2)).1
    exact hne (ConnectedComponent.eq_of_common_vertex hc hd)
  have edgeSubset : (Finset.univ : Finset G.ConnectedComponent).biUnion F ⊆ G.edgeFinset := by
    intro e he
    obtain ⟨c, _, hc⟩ := Finset.mem_biUnion.mp he
    revert hc
    refine Sym2.inductionOn e ?_
    intro u v hc
    have he : c.toSimpleGraph.spanningCoe.Adj u v := mem_edgeFinset.mp hc
    simpa using (c.adj_spanningCoe_toSimpleGraph.mp he).2
  have edgeCount : (∑ c : G.ConnectedComponent, (F c).card) ≤ edges G := by
    rw [← Finset.card_biUnion edgeDisjoint]
    exact Finset.card_le_card edgeSubset
  have each (c : G.ConnectedComponent) : c.supp.toFinset.card ≤ (F c).card + 1 := by
    have hc := c.connected_toSimpleGraph.card_vert_le_card_edgeSet_add_one
    have hv : c.supp.toFinset.card = Nat.card c := (Nat.card_eq_card_toFinset c.supp).symm
    have he : (F c).card = Nat.card c.toSimpleGraph.edgeSet := by
      change (c.toSimpleGraph.map (Function.Embedding.subtype _)).edgeFinset.card = _
      rw [card_edgeFinset_map, edgeFinset_card]
      exact Nat.card_eq_fintype_card.symm
    rwa [hv, he]
  have hsum : (∑ c : G.ConnectedComponent, c.supp.toFinset.card) ≤
      ∑ c : G.ConnectedComponent, ((F c).card + 1) :=
    Finset.sum_le_sum (fun c _ => each c)
  rw [vertexCount, Finset.sum_add_distrib] at hsum
  have hcomponents : (∑ _ : G.ConnectedComponent, (1 : Nat)) = components G := by
    simp [components, Nat.card_eq_fintype_card]
  omega

#print axioms novelty_spanning_forest_bound

theorem novelty_connected_triangle_relaxations {n : Nat} (G : SimpleGraph (Fin n))
    [DecidableRel G.Adj] (h : G.Connected) :
    chromatic G + n ≤ edges G + triangles G + 3 ∧
    chromatic G + 2 * n ≤ 2 * edges G + 2 * triangles G + 4 := by
  have hcycle := novelty_chromatic_cycle_rank G h
  have hedge := connected_edge_bound G h
  omega

#print axioms novelty_connected_triangle_relaxations

end AxiomGraphUniversal
