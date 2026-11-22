/-!
# Lean で試す数学の証明

各証明は `:= by` から始まる。途中の仮定と目標を表示したいときは、
調べたい手順の直前に、同じ字下げで `trace_state` を入れる。
-/

namespace LeanPractice

/-- 自然数の和が 10 なら、足す順番を入れ替えても和は 10 になる。 -/
theorem add_swap_ten (a b : Nat) (h : a + b = 10) : b + a = 10 := by
  rw [Nat.add_comm b a]
  exact h

/-- 「P かつ Q」なら「Q かつ P」が成り立つ。 -/
theorem and_swap (P Q : Prop) : P ∧ Q → Q ∧ P := by
  intro h       -- 前提 P ∧ Q を h と呼ぶ。
  constructor   -- 結論 Q ∧ P を、Q と P の二つの目標に分ける。
  · exact h.2   -- h の後半から Q を示す。
  · exact h.1   -- h の前半から P を示す。

/-- 自然数 n が偶数であるとは、n = 2 * k となる自然数 k が存在すること。 -/
def IsEven (n : Nat) : Prop := ∃ k : Nat, n = 2 * k

/-- 偶数どうしの和は偶数になる。 -/
theorem even_add_even (a b : Nat) (ha : IsEven a) (hb : IsEven b) :
    IsEven (a + b) := by
  obtain ⟨j, hj⟩ := ha  -- j と、等式 hj : a = 2 * j を取り出す。
  obtain ⟨k, hk⟩ := hb
  refine ⟨j + k, ?_⟩    -- 和の半分として j + k を選ぶ。残る目標は次の等式。
  -- calc は等式を順につなぐ。_ は直前の右辺、.symm は等式の向きを逆にする。
  calc
    a + b = 2 * j + 2 * k := by rw [hj, hk]
    _ = 2 * (j + k) := (Nat.mul_add 2 j k).symm

/-- 1 から n までの和。n = 0 のときは 0 とする。 -/
def sumTo : Nat → Nat
  | 0 => 0
  | n + 1 => sumTo n + (n + 1)

/-- 1 から n までの和を 2 倍すると n * (n + 1) になる。 -/
theorem two_mul_sumTo (n : Nat) : 2 * sumTo n = n * (n + 1) := by
  induction n with
  | zero => rfl  -- 定義から両辺とも 0 になる。
  | succ k ih =>
    -- 帰納法の仮定 ih は 2 * sumTo k = k * (k + 1)。これを使って k + 1 の場合を示す。
    calc
      2 * sumTo (k + 1)
          = 2 * sumTo k + 2 * (k + 1) := Nat.mul_add 2 (sumTo k) (k + 1)
      _ = k * (k + 1) + 2 * (k + 1) := by rw [ih]
      _ = (k + 2) * (k + 1) := (Nat.add_mul k 2 (k + 1)).symm
      _ = (k + 1) * (k + 2) := Nat.mul_comm (k + 2) (k + 1)

#check add_swap_ten
#check and_swap
#check even_add_even
#check two_mul_sumTo

end LeanPractice
