"""Lean adapters using neighborhood deletion and spanning trees."""


TRIANGLE_FREE_MATCHING_PROOF = """\
classical
  have neighbors_independent {V : Type} (H : SimpleGraph V) (h : H.CliqueFree 3) (v : V) :
      H.IsIndepSet (H.neighborSet v) := by
    intro a ha b hb hab e
    apply h {v, a, b}
    have hva : v ≠ a := H.ne_of_adj ha
    have hvb : v ≠ b := H.ne_of_adj hb
    refine ⟨?_, by simp [hva, hvb, hab]⟩
    intro x hx y hy hxy
    simp only [Finset.mem_coe, Finset.mem_insert, Finset.mem_singleton] at hx hy
    rcases hx with rfl | rfl | rfl <;> rcases hy with rfl | rfl | rfl
    all_goals first | contradiction | exact ha | exact ha.symm | exact hb | exact hb.symm | exact e | exact e.symm
  have aux (k : Nat) : ∀ (V : Type) [Fintype V] (H : SimpleGraph V),
      Fintype.card V = k → H.CliqueFree 3 →
      ∃ M : H.Subgraph, M.IsMatching ∧ H.Colorable (M.edgeSet.ncard + 1) := by
    induction k using Nat.strong_induction_on with
    | h k ih =>
      intro V inst H hk ht
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
        -- Remove the closed neighborhood and reserve one new color for its independent neighbors.
        let rest : Finset V := Finset.univ.filter (fun v => v ≠ a ∧ ¬ H.Adj a v)
        let J := H.induce (rest : Set V)
        have hmem (v : V) : v ∈ rest ↔ v ≠ a ∧ ¬ H.Adj a v := by simp [rest]
        have ha : a ∉ rest := fun h => ((hmem a).mp h).1 rfl
        have hb : b ∉ rest := fun h => ((hmem b).mp h).2 hab
        have hl : rest.card < k := by
          rw [← hk, ← Finset.card_univ]
          apply Finset.card_lt_card
          exact Finset.ssubset_iff_subset_ne.mpr ⟨Finset.subset_univ _, fun h => ha (h ▸ Finset.mem_univ a)⟩
        have hrest : Fintype.card (rest : Set V) = rest.card := Fintype.card_coe rest
        let incl : J →g H := ⟨Subtype.val, fun h => h⟩
        have hincl : Function.Injective incl := Subtype.val_injective
        have htJ : J.CliqueFree 3 := ht.comap ⟨incl, hincl⟩
        obtain ⟨M, hM, ⟨c⟩⟩ := ih rest.card hl _ J hrest htJ
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
        let f (v : V) : Fin (q + 1) :=
          if h : v ∈ rest then (c ⟨v, h⟩).castSucc
          else if H.Adj a v then Fin.last q else (Fin.castSucc ⟨0, Nat.zero_lt_succ _⟩)
        have hf0 (v : V) (hr : v ∉ rest) (hn : ¬ H.Adj a v) : v = a := by
          by_contra hv
          exact hr ((hmem v).mpr ⟨hv, hn⟩)
        refine ⟨SimpleGraph.Coloring.mk f ?_⟩
        intro u v huv
        by_cases hu : u ∈ rest <;> by_cases hv : v ∈ rest
        · simpa [f, hu, hv] using c.valid (show J.Adj ⟨u, hu⟩ ⟨v, hv⟩ from huv)
        · by_cases hav : H.Adj a v
          · simpa only [f, dite_eq_left hu, dite_eq_right hv, ite_eq_left hav] using Fin.castSucc_ne_last (c ⟨u, hu⟩)
          · exact (((hmem u).mp hu).2 ((hf0 v hv hav) ▸ huv.symm)).elim
        · by_cases hau : H.Adj a u
          · simpa [f, hu, hv, hau] using (Fin.castSucc_ne_last (c ⟨v, hv⟩)).symm
          · exact (((hmem v).mp hv).2 ((hf0 u hu hau) ▸ huv)).elim
        · by_cases hau : H.Adj a u <;> by_cases hav : H.Adj a v
          · exact (neighbors_independent H ht a hau hav (H.ne_of_adj huv) huv).elim
          · simp [f, hu, hv, hau, hav]
          · simp [f, hu, hv, hau, hav]
          · exact (H.ne_of_adj huv ((hf0 u hu hau).trans (hf0 v hv hav).symm)).elim
  obtain ⟨M, hM, hc⟩ := aux n (Fin n) G (Fintype.card_fin n) premise
  have hbound : BddAbove {k : Nat | ∃ M : G.Subgraph, M.IsMatching ∧ M.edgeSet.ncard = k} := by
    use Nat.card (Sym2 (Fin n))
    rintro k ⟨N, _, rfl⟩
    exact Set.ncard_le_card _
  have hm : M.edgeSet.ncard ≤ matching G := le_csSup hbound ⟨M, hM, rfl⟩
  have hc' := ENat.toNat_le_toNat hc.chromaticNumber_le (ENat.natCast_ne_top _)
  simp only [ENat.toNat_natCast] at hc'
  unfold chromatic
  omega"""


_CRITICAL_CORE = """\
  · let q := k - 1
    have hq : 0 < q := by omega
    have whole_bad : ¬ G.Colorable q := by
      intro hc
      have h := ENat.toNat_le_toNat hc.chromaticNumber_le (ENat.natCast_ne_top _)
      simp only [ENat.toNat_natCast] at h
      change k ≤ q at h
      omega
    -- Keep a smallest induced subgraph that still needs k colors.
    let bad (size : Nat) := ∃ s : Finset (Fin n), s.card = size ∧
      ¬ (G.induce (s : Set (Fin n))).Colorable q
    have hExists : ∃ size, bad size := by
      refine ⟨n, Finset.univ, by simp, ?_⟩
      rintro ⟨c⟩
      apply whole_bad
      exact ⟨SimpleGraph.Coloring.mk (fun v => c ⟨v, Finset.mem_univ v⟩) (fun h => c.valid h)⟩
    obtain ⟨s, hsize, hbad⟩ := Nat.find_spec hExists
    have minimal (t : Finset (Fin n)) (ht : t.card < s.card) :
        (G.induce (t : Set (Fin n))).Colorable q := by
      by_contra hne
      exact Nat.find_min hExists (hsize ▸ ht) ⟨t, rfl, hne⟩
    let J := G.induce (s : Set (Fin n))
    have size_card : Fintype.card (s : Set (Fin n)) = s.card := Fintype.card_coe s
    have size_lower : k ≤ s.card := by
      by_contra! hl
      have hColor : J.Colorable ((Fintype.card (s : Set (Fin n)))) :=
        SimpleGraph.chromaticNumber_le_iff_colorable.mp J.chromaticNumber_le_card
      exact hbad (SimpleGraph.Colorable.mono (by rw [size_card]; omega) hColor)
    have nonempty : Nonempty (s : Set (Fin n)) := by
      obtain ⟨v, hv⟩ := Finset.card_pos.mp (by omega : 0 < s.card)
      exact ⟨⟨v, hv⟩⟩
    -- Lower degree would leave an unused color when the removed vertex is restored.
    have minDeg (v : (s : Set (Fin n))) : q ≤ J.degree v := by
      by_contra! low
      let t := s.erase v.val
      have hsm : t.card < s.card := Finset.card_erase_lt_of_mem v.property
      obtain ⟨c⟩ := minimal t hsm
      have ht (w : (s : Set (Fin n))) (hw : w ≠ v) : w.val ∈ t :=
        Finset.mem_erase.mpr ⟨fun h => hw (Subtype.ext h), w.property⟩
      let oldColor (w : (s : Set (Fin n))) : Fin q :=
        if hw : w ≠ v then c ⟨w.val, ht w hw⟩ else ⟨0, hq⟩
      let used := (J.neighborFinset v).image oldColor
      have hused : used.card < (Finset.univ : Finset (Fin q)).card := by
        rw [Finset.card_univ, Fintype.card_fin]
        exact Finset.card_image_le.trans_lt low
      obtain ⟨new, _, hfresh⟩ := Finset.exists_mem_notMem_of_card_lt_card hused
      have different (w : (s : Set (Fin n))) (hw : J.Adj v w) : new ≠ oldColor w := by
        intro he
        apply hfresh
        exact Finset.mem_image.mpr ⟨w, (J.mem_neighborFinset v w).mpr hw, he.symm⟩
      apply hbad
      refine ⟨SimpleGraph.Coloring.mk (Function.update oldColor v new) ?_⟩
      intro a b hab
      by_cases ha : a = v
      · subst a
        simpa [(J.ne_of_adj hab).symm] using different b hab
      · by_cases hb : b = v
        · subst b
          simpa [ha] using (different a hab.symm).symm
        · simpa [ha, hb, oldColor] using c.valid
            (show (G.induce (t : Set (Fin n))).Adj ⟨a.val, ht a ha⟩ ⟨b.val, ht b hb⟩ from hab)
    have handshaking : s.card * q ≤ 2 * J.edgeFinset.card := by
      have hsum := Finset.sum_le_sum (s := Finset.univ) (fun v _ => minDeg v)
      rw [J.sum_degrees_eq_twice_card_edges] at hsum
      simpa [size_card] using hsum
"""

_SPANNING_TREE_COUNT = """\
    -- Count the edges of the core beyond a spanning tree of the ambient graph.
    let f : (s : Set (Fin n)) ↪ Fin n := Function.Embedding.subtype _
    let K := J.map f
    have hK : K ≤ G := SimpleGraph.map_comap_le f G
    obtain ⟨T, hTG, hT⟩ := premise.exists_isTree_le
    let U := T.comap f
    have hU : U.IsAcyclic := hT.isAcyclic.of_comap f
    obtain ⟨F, hUF, _, hF⟩ :=
      (SimpleGraph.connected_top (V := (s : Set (Fin n)))).exists_isTree_le_of_le_of_isAcyclic le_top hU
    have hsmall : U.edgeFinset.card + 1 ≤ s.card := by
      have hcard := hF.card_edgeFinset
      rw [size_card] at hcard
      have hmono := Finset.card_le_card (SimpleGraph.edgeFinset_mono hUF)
      omega
    have hintersection : T ⊓ K = U.map f := by
      ext u v
      constructor
      · rintro ⟨ht, ⟨_, a, b, _, rfl, rfl⟩⟩
        exact ⟨T.ne_of_adj ht, a, b, ht, rfl, rfl⟩
      · rintro ⟨hne, a, b, ht, rfl, rfl⟩
        exact ⟨ht, ⟨hne, a, b, hTG ht, rfl, rfl⟩⟩
    have hinf : (T.edgeFinset ∩ K.edgeFinset).card + 1 ≤ s.card := by
      have same_edges : (T ⊓ K).edgeFinset = (U.map f).edgeFinset := by
        ext e
        simp only [SimpleGraph.mem_edgeFinset, hintersection]
      rw [← SimpleGraph.edgeFinset_inf, same_edges, SimpleGraph.card_edgeFinset_map]
      exact hsmall
    have hKcard : K.edgeFinset.card = J.edgeFinset.card := SimpleGraph.card_edgeFinset_map f J
    have htree := hT.card_edgeFinset
    rw [Fintype.card_fin] at htree
    have hunion := Finset.card_le_card (SimpleGraph.edgeFinset_mono (sup_le hTG hK))
    rw [SimpleGraph.edgeFinset_sup] at hunion
    have hcount := Finset.card_union_add_card_inter T.edgeFinset K.edgeFinset
"""

CONNECTED_CHROMATIC_EDGES_PROOF = """\
classical
  let k := chromatic G
  change (1 : Int) * n + (-1 : Int) * (edges G : Int) + (2 : Int) * k ≤ 6
  have hconn := connected_edge_bound G premise
  by_cases hk : 3 ≤ k
""" + _CRITICAL_CORE + _SPANNING_TREE_COUNT + """    have mul_split : s.card * q = s.card * (k - 3) + 2 * s.card := by
      have h : q = k - 3 + 2 := by omega
      rw [h, Nat.mul_add, Nat.mul_comm s.card 2]
    have deg_excess : 4 * (k - 3) ≤ s.card * (k - 3) := by
      by_cases h4 : 4 ≤ k
      · exact Nat.mul_le_mul_right _ (h4.trans size_lower)
      · have h3 : k - 3 = 0 := by omega
        simp [h3]
    unfold edges
    omega
  · omega"""


def critical_edge_tangent(slope, connected):
    """Specialize the discrete tangent of the critical-subgraph edge bound."""
    if connected:
        tree_setup = "  have conn := connected_edge_bound G premise\n"
        count = _SPANNING_TREE_COUNT + """    have product : k * (k - 3) ≤ s.card * (k - 3) :=
      Nat.mul_le_mul_right _ size_lower
    have split : s.card * q = s.card * (k - 3) + 2 * s.card := by
      have eq : q = k - 3 + 2 := by omega
      rw [eq, Nat.mul_add, Nat.mul_comm s.card 2]
    have bound : k * (k - 3) + 2 * n ≤ 2 * G.edgeFinset.card := by omega
"""
        center = slope + 1
        offset = 3
    else:
        tree_setup = ""
        count = """    let f : (s : Set (Fin n)) ↪ Fin n := Function.Embedding.subtype _
    have mono := Finset.card_le_card (SimpleGraph.edgeFinset_mono (SimpleGraph.map_comap_le f G))
    change (J.map f).edgeFinset.card ≤ G.edgeFinset.card at mono
    rw [SimpleGraph.card_edgeFinset_map] at mono
    have bound : k * (k - 1) ≤ 2 * G.edgeFinset.card :=
      (Nat.mul_le_mul_right q size_lower).trans (handshaking.trans (by omega))
"""
        center = slope
        offset = 1
    threshold = 3 if connected else 2
    cast_rules = "Int.natCast_mul, Int.natCast_add" if connected else "Int.natCast_mul"
    return ("classical\n  let k := chromatic G\n" + tree_setup +
            f"  by_cases hk : {threshold} ≤ k\n" + _CRITICAL_CORE + count +
            f"""    have gap : 0 ≤ ((k : Int) - {center}) * ((k : Int) - {center+1}) := by
      by_cases h : (k : Int) ≤ {center}
      · exact mul_nonneg_of_nonpos_of_nonpos (by omega) (by omega)
      · exact mul_nonneg (by omega) (by omega)
    have cast_sub : ((k - {offset} : Nat) : Int) = (k : Int) - {offset} := by omega
    have linear := Int.ofNat_le.mpr bound
    simp only [{cast_rules}, cast_sub] at linear
    change _ ≤ (_ : Int)
    unfold edges
    dsimp [k] at linear gap
    grind only
  · have small : chromatic G < {threshold} := by omega
    omega""")
