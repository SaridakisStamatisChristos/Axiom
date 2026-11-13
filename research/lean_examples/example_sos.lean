-- Generated exclusively from a separately validated AXIOM v0.2 certificate.
-- Statement SHA-256: 5e41838d7e9792d8ffda1f351576b0cc1bc794c86ada2d26d70d1dbce063c546
import Mathlib.Tactic.Ring
import Mathlib.Tactic.Linarith

theorem axiom_5e41838d7e9792d8ffda1f35 (x : Int) : ((x ^ 2) + (0 : Int)) ≥ (0 : Int) := by
  have hs0 : (0 : Int) ≤ ((((2 : Int) * (x ^ 1)))) ^ 2 := sq_nonneg ((((2 : Int) * (x ^ 1))))
  have hcert : ((4 : Int) * (((x ^ 2) + (0 : Int)) - (0 : Int))) = (((1 : Int) * ((((2 : Int) * (x ^ 1)))) ^ 2) + (0 : Int)) := by ring
  nlinarith [hs0]

#print axioms axiom_5e41838d7e9792d8ffda1f35
