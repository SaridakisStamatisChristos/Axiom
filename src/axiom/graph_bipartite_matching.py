"""Lean proof of the reverse matching and independence bound for bipartite graphs."""

BIPARTITE_MATCHING_PROOF = """\
classical
  obtain ⟨color⟩ := premise
  obtain ⟨S, hS⟩ := G.exists_isNIndepSet_indepNum
  let C : Set (Fin n) := {v | v ∉ S}
  let neighbors (v : C) := S.filter (G.Adj (v : Fin n))
  -- Replacing the neighbors of an independent subset by that subset
  -- cannot enlarge a maximum independent set.
  have swap_bound (t : Finset C) (hi : G.IsIndepSet (↑(t.image Subtype.val))) :
      t.card ≤ (t.biUnion neighbors).card := by
    let T := t.image Subtype.val
    let N := t.biUnion neighbors
    have hNS : N ⊆ S := by
      intro v hv
      obtain ⟨u, _, hu⟩ := Finset.mem_biUnion.mp hv
      exact (Finset.mem_filter.mp hu).1
    have hTS : Disjoint T (S \\ N) := by
      rw [Finset.disjoint_left]
      intro v hv hs
      obtain ⟨u, _, rfl⟩ := Finset.mem_image.mp hv
      exact u.property (Finset.mem_sdiff.mp hs).1
    have hcross {u v : Fin n} (hu : u ∈ T) (hv : v ∈ S \\ N) : ¬G.Adj u v := by
      obtain ⟨x, hx, rfl⟩ := Finset.mem_image.mp hu
      intro ha
      exact (Finset.mem_sdiff.mp hv).2
        (Finset.mem_biUnion.mpr ⟨x, hx, Finset.mem_filter.mpr ⟨(Finset.mem_sdiff.mp hv).1, ha⟩⟩)
    have hind : G.IsIndepSet (↑(T ∪ (S \\ N))) := by
      intro u hu v hv hne ha
      rcases Finset.mem_union.mp hu with hu | hu <;> rcases Finset.mem_union.mp hv with hv | hv
      · exact hi hu hv hne ha
      · exact hcross hu hv ha
      · exact hcross hv hu ha.symm
      · exact hS.isIndepSet (Finset.mem_sdiff.mp hu).1 (Finset.mem_sdiff.mp hv).1 hne ha
    have hb := hind.card_le_indepNum
    rw [Finset.card_union_of_disjoint hTS, Finset.card_sdiff_of_subset hNS, ← hS.card_eq] at hb
    rw [Finset.card_image_of_injective _ Subtype.val_injective] at hb
    have hle := Finset.card_le_card hNS
    change t.card ≤ N.card
    omega
  have color_adj {u v : Fin n} (h : G.Adj u v) : color u ≠ color v := color.valid h
  have same_color {u v : Fin 2} (hu : u ≠ 0) (hv : v ≠ 0) : u = v := by
    fin_cases u <;> fin_cases v <;> simp_all
  have hall (s : Finset C) : s.card ≤ (s.biUnion neighbors).card := by
    let p (v : C) := color v = 0
    let A := s.filter p
    let B := s.filter (fun v => ¬p v)
    have ha : G.IsIndepSet (↑(A.image Subtype.val)) := by
      intro u hu v hv _ hadj
      obtain ⟨x, hx, rfl⟩ := Finset.mem_image.mp hu
      obtain ⟨y, hy, rfl⟩ := Finset.mem_image.mp hv
      exact color_adj hadj ((Finset.mem_filter.mp hx).2.trans (Finset.mem_filter.mp hy).2.symm)
    have hb : G.IsIndepSet (↑(B.image Subtype.val)) := by
      intro u hu v hv _ hadj
      obtain ⟨x, hx, rfl⟩ := Finset.mem_image.mp hu
      obtain ⟨y, hy, rfl⟩ := Finset.mem_image.mp hv
      exact color_adj hadj (same_color (Finset.mem_filter.mp hx).2 (Finset.mem_filter.mp hy).2)
    have hd : Disjoint (A.biUnion neighbors) (B.biUnion neighbors) := by
      rw [Finset.disjoint_left]
      intro v ha hb
      obtain ⟨x, hx, hxv⟩ := Finset.mem_biUnion.mp ha
      obtain ⟨y, hy, hyv⟩ := Finset.mem_biUnion.mp hb
      have hx0 : color x = 0 := (Finset.mem_filter.mp hx).2
      have hv0 : color v ≠ 0 := fun h =>
        color_adj (Finset.mem_filter.mp hxv).2 (hx0.trans h.symm)
      exact color_adj (Finset.mem_filter.mp hyv).2 (same_color (Finset.mem_filter.mp hy).2 hv0)
    have hsubset : (A.biUnion neighbors) ∪ (B.biUnion neighbors) ⊆ s.biUnion neighbors := by
      intro v hv
      rcases Finset.mem_union.mp hv with hv | hv <;>
        obtain ⟨x, hx, hxv⟩ := Finset.mem_biUnion.mp hv <;>
        exact Finset.mem_biUnion.mpr ⟨x, (Finset.mem_filter.mp hx).1, hxv⟩
    have hcard := Finset.card_le_card hsubset
    rw [Finset.card_union_of_disjoint hd] at hcard
    have hsum : A.card + B.card = s.card := Finset.card_filter_add_card_filter_not p
    exact hsum ▸ ((Nat.add_le_add (swap_bound A ha) (swap_bound B hb)).trans hcard)
  obtain ⟨f, hf, hfedge⟩ := (Finset.all_card_le_biUnion_card_iff_exists_injective neighbors).mp hall
  have hfS (v : C) : f v ∈ S := (Finset.mem_filter.mp (hfedge v)).1
  have hfA (v : C) : G.Adj (v : Fin n) (f v) := (Finset.mem_filter.mp (hfedge v)).2
  have hd : Disjoint C (Set.range f) := by
    rw [Set.disjoint_left]
    rintro _ hv ⟨u, rfl⟩
    exact hv (hfS u)
  let e := Equiv.ofInjective f hf
  obtain ⟨M, hverts, hM⟩ := SimpleGraph.Subgraph.IsMatching.exists_of_disjoint_sets_of_equiv hd e hfA
  have hVertsCard : M.verts.ncard = 2 * C.ncard := by
    rw [hverts, Set.ncard_union_eq hd, Set.ncard_range_of_injective hf, Nat.card_coe_set_eq]
    omega
  let : Fintype M.verts := Fintype.ofFinite _
  let : DecidableRel M.coe.Adj := Classical.decRel _
  have hDegree : ∀ v : M.verts, M.coe.degree v = 1 := by
    have h := SimpleGraph.Subgraph.isMatching_iff_forall_degree.mp hM
    intro v
    simpa [SimpleGraph.Subgraph.degree] using h v v.property
  have hSum : M.verts.ncard = 2 * M.coe.edgeFinset.card := by
    rw [← Set.fintypeCard_eq_ncard]
    calc
      Fintype.card M.verts = ∑ _ : M.verts, (1 : Nat) := by simp
      _ = ∑ v, M.coe.degree v := by
        apply Finset.sum_congr rfl
        intro v _
        have hv := (hDegree v).symm
        simp only [← SimpleGraph.ncard_neighborSet] at hv ⊢
        exact hv
      _ = 2 * M.coe.edgeFinset.card := by
        simpa only [← SimpleGraph.ncard_neighborSet] using M.coe.sum_degrees_eq_twice_card_edges
  have hEdgeCard : M.coe.edgeFinset.card = M.edgeSet.ncard := by
    rw [SimpleGraph.edgeFinset_card, Set.fintypeCard_eq_ncard]
    rw [← M.image_coe_edgeSet_coe, Set.ncard_image_of_injective _ (Sym2.map.injective Subtype.val_injective)]
  have hm : M.edgeSet.ncard ≤ matching G := by
    apply le_csSup
    · refine ⟨G.edgeSet.ncard, ?_⟩
      rintro _ ⟨M', _, rfl⟩
      exact Set.ncard_le_ncard M'.edgeSet_subset
    · exact ⟨M, hM, rfl⟩
  have hC : C.ncard = (Sᶜ : Finset (Fin n)).card := by
    have heq : C = ↑(Sᶜ : Finset (Fin n)) := by
      ext v
      simp [C]
    rw [heq, Set.ncard_coe_finset]
  have hTotal := S.card_add_card_compl
  have hIndep := hS.card_eq
  simp only [Fintype.card_fin] at hTotal
  simp only [independence]
  omega"""
