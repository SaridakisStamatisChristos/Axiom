"""Lean proof body for the chromatic bound from component representatives."""

COMPONENT_COLORING_PROOF = """\
classical
  have surj : Function.Surjective G.connectedComponentMk := Quot.mk_surjective
  let rep : G.ConnectedComponent → Fin n := fun c => (surj c).choose
  have section_rep : Function.LeftInverse G.connectedComponentMk rep :=
    fun c => (surj c).choose_spec
  let reps : Finset (Fin n) := Finset.univ.image rep
  have hreps : reps.card = components G := by
    simp [reps, Finset.card_image_of_injective _ section_rep.injective,
      components, Nat.card_eq_fintype_card]
  -- Share one color across all representatives and use distinct colors elsewhere.
  let color (v : Fin n) : Option ↥(repsᶜ : Finset (Fin n)) :=
    if h : v ∈ reps then none else some ⟨v, Finset.mem_compl.mpr h⟩
  have valid {u v : Fin n} (h : G.Adj u v) : color u ≠ color v := by
    intro heq
    by_cases hu : u ∈ reps <;> by_cases hv : v ∈ reps
    · obtain ⟨a, _, rfl⟩ := Finset.mem_image.mp hu
      obtain ⟨b, _, rfl⟩ := Finset.mem_image.mp hv
      have hc := SimpleGraph.ConnectedComponent.sound h.reachable
      rw [section_rep a, section_rep b] at hc
      exact (G.ne_of_adj h) (congrArg rep hc)
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
  omega"""
