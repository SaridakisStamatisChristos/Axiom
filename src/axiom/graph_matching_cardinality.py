"""Lean proof of the vertex-cardinality bound on matchings."""

MATCHING_CARDINALITY_PROOF = """\
classical
  have bound : matching G ≤ n / 2 := by
    unfold matching
    apply csSup_le'
    rintro k ⟨M, hM, rfl⟩
    let : Fintype M.verts := Fintype.ofFinite _
    let : DecidableRel M.coe.Adj := Classical.decRel _
    have degree_one (v : M.verts) : M.coe.degree v = 1 := by
      have h := SimpleGraph.Subgraph.isMatching_iff_forall_degree.mp hM
      simpa [SimpleGraph.Subgraph.degree] using h v v.property
    have vertex_count : Fintype.card M.verts = 2 * M.coe.edgeFinset.card := by
      calc
        Fintype.card M.verts = ∑ _ : M.verts, (1 : Nat) := by simp
        _ = ∑ v, M.coe.degree v := by
          apply Finset.sum_congr rfl
          intro v _
          have hv := (degree_one v).symm
          simp only [← SimpleGraph.ncard_neighborSet] at hv ⊢
          exact hv
        _ = 2 * M.coe.edgeFinset.card := by
          simpa only [← SimpleGraph.ncard_neighborSet] using M.coe.sum_degrees_eq_twice_card_edges
    have edge_count : M.coe.edgeFinset.card = M.edgeSet.ncard := by
      rw [SimpleGraph.edgeFinset_card, Set.fintypeCard_eq_ncard]
      rw [← M.image_coe_edgeSet_coe,
        Set.ncard_image_of_injective _ (Sym2.map.injective Subtype.val_injective)]
    have vertex_bound : Fintype.card M.verts ≤ n := by
      simpa only [Fintype.card_fin] using Fintype.card_le_of_injective
        (fun v : M.verts => v.val) Subtype.val_injective
    omega
  omega"""
