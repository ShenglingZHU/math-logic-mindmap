---
cssclasses: [math-proof-note]
proof_slug: two-variable-am-gm
lang: en
---

# Two-variable arithmetic-geometric mean inequality

[[mindmap/two-variable-am-gm.canvas|Open proof map]]

Mathematical status: Proved (mathematical conclusion); Proof standard: `strict`.

See [[note/two-variable-am-gm/_review-checklist|Review record]] and its artifact version for visual status; generation is not evidence of a successful visual review.

## Theorem statement

$\forall a,b\in[0,\infty),\quad\frac{a+b}{2}\ge\sqrt{ab}$

## Assumptions

- $a,b$ are nonnegative real numbers.

## Field

Elementary inequalities over the real numbers.

## Background

The theorem compares the arithmetic and geometric means of two nonnegative real numbers.

## Role / importance

The two-variable arithmetic-geometric mean inequality is a fundamental comparison between two means and a building block for elementary inequalities.

## Purpose

It bounds the geometric mean by the arithmetic mean and supports estimates and optimization for nonnegative quantities; equality occurs when the inputs coincide.

## Proof approach / strategy

Follow the symbolic square-nonnegativity route described by Joseph Fields in https://math.libretexts.org/Bookshelves/Mathematical_Logic_and_Proof/Gentle_Introduction_to_the_Art_of_Mathematics_(Fields)/03:_Proof_Techniques_I/3.02:_More_Direct_Proofs . Apply the square rule to $a-b$, retain the squared comparison as the distinct stage result, then verify nonnegative sides before using square-root monotonicity. The principal-root simplifications are one-use consequences of A1 and the definition of the nonnegative square root, so they stay in the combination note.

## Proof tools

Nonnegativity of real squares, elementary expansion, monotonicity of the principal square root, and its defining uniqueness.

## Global symbols

| Symbol | Mathematical definition or role | Range / unit | Meaning / interpretation (if applicable) |
| --- | --- | --- | --- |
| $a$ | First input | Nonnegative real | First number being compared |
| $b$ | Second input | Nonnegative real | Second number being compared |

## Proof flow

### Stage S1 · Inputs and square positivity

Fix $a,b\ge0$ and identify the square-positivity fact used first.

[[note/two-variable-am-gm/A1|A1 · Nonnegative inputs]], [[note/two-variable-am-gm/K1|K1 · Square nonnegativity]]

### Stage S2 · The squared bound

Apply square positivity to $a-b$ and record $(a+b)^2\ge4ab$.

[[note/two-variable-am-gm/C1|C1 · Derive the squared bound]], [[note/two-variable-am-gm/R1|R1 · Squared comparison]]

### Stage S3 · Taking square roots

Check nonnegative sides, invoke square-root monotonicity, and conclude the mean inequality.

[[note/two-variable-am-gm/K2|K2 · Square-root monotonicity]], [[note/two-variable-am-gm/C2|C2 · Take square roots]], [[note/two-variable-am-gm/T1|T1 · Arithmetic-geometric mean]]



## Node index

- [[note/two-variable-am-gm/A1|A1 · Nonnegative inputs]]
- [[note/two-variable-am-gm/K1|K1 · Square nonnegativity]]
- [[note/two-variable-am-gm/C1|C1 · Derive the squared bound]]
- [[note/two-variable-am-gm/R1|R1 · Squared comparison]]
- [[note/two-variable-am-gm/K2|K2 · Square-root monotonicity]]
- [[note/two-variable-am-gm/C2|C2 · Take square roots]]
- [[note/two-variable-am-gm/T1|T1 · Arithmetic-geometric mean]]

## Explanatory edge index

## Personal notes
<!-- personal:start -->
<!-- personal:end -->
