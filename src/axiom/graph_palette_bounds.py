"""Lean certificates for coloring from independent sets and matchings."""


INDEPENDENT_PALETTE = """\
classical
  obtain ⟨reps, hs⟩ := G.exists_isNIndepSet_indepNum
  let color (v : Fin n) : Option ↥(repsᶜ : Finset (Fin n)) :=
    if h : v ∈ reps then none else some ⟨v, Finset.mem_compl.mpr h⟩
  have valid {u v : Fin n} (h : G.Adj u v) : color u ≠ color v := by
    intro heq
    by_cases hu : u ∈ reps <;> by_cases hv : v ∈ reps
    · exact hs.isIndepSet hu hv (G.ne_of_adj h) h
    · simp [color, hu, hv] at heq
    · simp [color, hu, hv] at heq
    · have huv : u = v := by simpa [color, hu, hv] using heq
      exact (G.ne_of_adj h) huv
  have hcolor := (SimpleGraph.Coloring.mk color valid).colorable.chromaticNumber_le
  have hnat := ENat.toNat_le_toNat hcolor (ENat.natCast_lt_top _).ne
  have hc : chromatic G ≤ (repsᶜ : Finset (Fin n)).card + 1 := by
    simpa only [chromatic, Fintype.card_option, Fintype.card_coe, ENat.toNat_natCast] using hnat
  have hsum := reps.card_add_card_compl
  simp only [Fintype.card_fin] at hsum
  have hcard := hs.card_eq
  unfold independence
  omega"""


MATCHING_PALETTE = """\
classical
  have aux (k : Nat) : ∀ (V : Type) [Fintype V] (H : SimpleGraph V),
      Fintype.card V = k →
      ∃ M : H.Subgraph, M.IsMatching ∧ H.Colorable (2 * M.edgeSet.ncard + 1) := by
    induction k using Nat.strong_induction_on with
    | h k ih =>
      intro V inst H hk
      by_cases hh : H = ⊥
      · refine ⟨⊥, ?_, ?_⟩
        · simp [SimpleGraph.Subgraph.IsMatching]
        · simpa using (SimpleGraph.colorable_one_iff.mpr hh)
      · have hpair : ∃ a b : V, H.Adj a b := by
          by_contra! h
          apply hh
          ext a b
          simp [h]
        obtain ⟨a, b, hab⟩ := hpair
        -- Reserve two colors for the endpoints of this matching edge.
        let rest : Finset V := Finset.univ.filter (fun v => v ≠ a ∧ v ≠ b)
        let J := H.induce (rest : Set V)
        have hmem (v : V) : v ∈ rest ↔ v ≠ a ∧ v ≠ b := by simp [rest]
        have ha : a ∉ rest := fun h => ((hmem a).mp h).1 rfl
        have hb : b ∉ rest := fun h => ((hmem b).mp h).2 rfl
        have hl : rest.card < k := by
          rw [← hk, ← Finset.card_univ]
          apply Finset.card_lt_card
          exact Finset.ssubset_iff_subset_ne.mpr ⟨Finset.subset_univ _, fun h => ha (h ▸ Finset.mem_univ a)⟩
        have hrest : Fintype.card (rest : Set V) = rest.card := Fintype.card_coe rest
        let incl : J →g H := ⟨Subtype.val, fun h => h⟩
        have hincl : Function.Injective incl := Subtype.val_injective
        obtain ⟨M, hM, ⟨c⟩⟩ := ih rest.card hl _ J hrest
        let q := M.edgeSet.ncard + 1
        -- The edge ab is disjoint from the matching pulled back from the remainder.
        let N := M.map incl
        let e := H.subgraphOfAdj hab
        have hN := hM.map incl hincl
        have he : e.IsMatching := SimpleGraph.Subgraph.IsMatching.subgraphOfAdj hab
        have hd : Disjoint N.verts e.verts := by
          rw [Set.disjoint_left]
          rintro _ ⟨v, hv, rfl⟩ he'
          change v.val ∈ e.verts at he'
          have he'' : v.val = a ∨ v.val = b := by
            simpa [e, incl, SimpleGraph.subgraphOfAdj_verts] using he'
          rcases he'' with h | h
          · exact ha (h ▸ v.property)
          · exact hb (h ▸ v.property)
        have hedges : (N ⊔ e).edgeSet.ncard = q := by
          rw [SimpleGraph.Subgraph.edgeSet_sup, Set.ncard_union_eq (SimpleGraph.Subgraph.disjoint_verts_iff_disjoint.mp hd).edgeSet]
          rw [SimpleGraph.Subgraph.edgeSet_map, Set.ncard_image_of_injective _ (Sym2.map.injective hincl)]
          simp [e, q, SimpleGraph.edgeSet_subgraphOfAdj]
        refine ⟨N ⊔ e, hN.sup he (by rwa [hN.support_eq_verts, he.support_eq_verts]), ?_⟩
        rw [hedges]
        let p := 2 * M.edgeSet.ncard + 1
        have size : 2 * q + 1 = p + 2 := by dsimp [q, p]; omega
        rw [size]
        let f (v : V) : Fin (p + 2) :=
          if h : v ∈ rest then (c ⟨v, h⟩).castSucc.castSucc
          else if v = a then (Fin.last p).castSucc else Fin.last (p + 1)
        refine ⟨SimpleGraph.Coloring.mk f ?_⟩
        intro u v huv
        by_cases hu : u ∈ rest <;> by_cases hv : v ∈ rest
        · simpa [f, hu, hv] using c.valid (show J.Adj ⟨u, hu⟩ ⟨v, hv⟩ from huv)
        · by_cases hva : v = a
          · simpa only [f, dite_eq_left hu, dite_eq_right hv, ite_eq_left hva] using
              (fun h => Fin.castSucc_ne_last (c ⟨u, hu⟩) (Fin.castSucc_inj.mp h) : (c ⟨u, hu⟩).castSucc.castSucc ≠ (Fin.last p).castSucc)
          · simpa only [f, dite_eq_left hu, dite_eq_right hv, ite_eq_right hva] using
              (Fin.castSucc_ne_last (c ⟨u, hu⟩).castSucc)
        · by_cases hua : u = a
          · simpa only [f, dite_eq_right hu, dite_eq_left hv, ite_eq_left hua] using
              (fun h => Fin.castSucc_ne_last (c ⟨v, hv⟩) (Fin.castSucc_inj.mp h.symm) : (Fin.last p).castSucc ≠ (c ⟨v, hv⟩).castSucc.castSucc)
          · simpa only [f, dite_eq_right hu, dite_eq_left hv, ite_eq_right hua] using
              (Fin.castSucc_ne_last (c ⟨v, hv⟩).castSucc).symm
        · have onlyEnds (w : V) (hw : w ∉ rest) : w = a ∨ w = b := by
            by_cases h : w = a
            · exact Or.inl h
            · exact Or.inr (of_not_not (fun hb => hw ((hmem w).mpr ⟨h, hb⟩)))
          rcases onlyEnds u hu with rfl | rfl <;> rcases onlyEnds v hv with rfl | rfl
          all_goals first | exact (H.ne_of_adj huv rfl).elim | simp [f, ha, hb, (H.ne_of_adj hab).symm, Fin.castSucc_ne_last, Ne.symm (Fin.castSucc_ne_last _)]
  obtain ⟨M, hM, hc⟩ := aux n (Fin n) G (Fintype.card_fin n)
  have hbound : BddAbove {k : Nat | ∃ M : G.Subgraph, M.IsMatching ∧ M.edgeSet.ncard = k} := by
    use Nat.card (Sym2 (Fin n))
    rintro k ⟨N, _, rfl⟩
    exact Set.ncard_le_card _
  have hm : M.edgeSet.ncard ≤ matching G := le_csSup hbound ⟨M, hM, rfl⟩
  have hc' := ENat.toNat_le_toNat hc.chromaticNumber_le (ENat.natCast_ne_top _)
  simp only [ENat.toNat_natCast] at hc'
  unfold chromatic
  omega"""
