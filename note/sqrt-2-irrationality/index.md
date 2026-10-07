---
cssclasses: [math-proof-note]
proof_slug: sqrt-2-irrationality
lang: en
---

# The irrationality of $\sqrt{2}$

[[mindmap/sqrt-2-irrationality.canvas|Open proof map]]

Mathematical status: Proved (mathematical conclusion); Proof standard: `strict`.

See [[note/sqrt-2-irrationality/_review-checklist|Review record]] and its artifact version for visual status; generation is not evidence of a successful visual review.

## Theorem statement

$\sqrt{2}\notin\mathbb{Q}$

## Assumptions

- No additional assumptions are required.

## Field

Elementary number theory and proof methods.

## Background

A reduced fraction provides a finite arithmetic witness to test a rationality assumption.

## Role / importance

A compact example that makes a contradiction and two nested scope closures visible.

## Purpose

Demonstrate that the proof model can express reductio with a scoped existential witness.

## Proof approach / strategy

Use the classical reduced-fraction contradiction presented by Harvey Mudd College (https://math.hmc.edu/funfacts/square-root-of-two-is-irrational/). It matches the unconditional claim and needs only integer parity. This model expands the source's reduced-fraction choice into a visible existential-witness scope, reuses one parity theorem node twice, and closes that scope before reductio.

## Proof tools

Reduced fractions, parity of squares, existential elimination, and reductio.

## Global symbols

| Symbol | Mathematical definition or role | Range / unit | Meaning / interpretation (if applicable) |
| --- | --- | --- | --- |
| $\sqrt{2}$ | The positive square root of two | Positive real | The number under study |
| $\mathbb{Q}$ | Set of rational numbers | Set | The set whose membership is denied |
| $\mathbb{Z}$ | Set of integers | Set | Domain of numerator and denominator |
| $\gcd$ | Greatest common divisor | Positive integer on nonzero pairs | Tests whether a fraction is reduced |
| $\mid$ | Integer divisibility relation | Not applicable | Records evenness through divisibility by two |
| $\bot$ | Contradiction | Not applicable | An impossible conclusion under the local assumption |

## Proof flow

### Stage S1 · Rationality and reduction

The temporary hypothesis and reduced-fraction theorem yield a reduced representation.

[[note/sqrt-2-irrationality/H1|H1 · Assume rationality]], [[note/sqrt-2-irrationality/K1|K1 · Reduced fraction theorem]], [[note/sqrt-2-irrationality/K2|K2 · Parity of squares]], [[note/sqrt-2-irrationality/D1|D1 · Square root property]], [[note/sqrt-2-irrationality/C1|C1 · Normalize rationality]], [[note/sqrt-2-irrationality/R1|R1 · Reduced representation exists]]

### Stage S2 · Choose the fraction

Take fresh integral witnesses and record the positive denominator and coprimality.

[[note/sqrt-2-irrationality/L1|L1 · Choose reduced witnesses]], [[note/sqrt-2-irrationality/R2|R2 · Witness conditions]]

### Stage S3 · Numerator parity

The square equation and the parity theorem make the numerator even.

[[note/sqrt-2-irrationality/C2|C2 · Square the representation]], [[note/sqrt-2-irrationality/R3|R3 · Square relation]], [[note/sqrt-2-irrationality/C3|C3 · Infer numerator parity]], [[note/sqrt-2-irrationality/R4|R4 · Even numerator]]

### Stage S4 · Denominator parity

The even numerator makes the denominator square, then the denominator, even.

[[note/sqrt-2-irrationality/C4|C4 · Infer denominator square parity]], [[note/sqrt-2-irrationality/R5|R5 · Even denominator square]], [[note/sqrt-2-irrationality/C5|C5 · Infer denominator parity]], [[note/sqrt-2-irrationality/R6|R6 · Even denominator]]

### Stage S5 · Contradiction and discharge

Both witnesses are even despite being coprime; close the witness and rationality scopes in order.

[[note/sqrt-2-irrationality/C6|C6 · Expose the contradiction]], [[note/sqrt-2-irrationality/X1|X1 · Coprimality contradiction]], [[note/sqrt-2-irrationality/X2|X2 · Witness-free contradiction]], [[note/sqrt-2-irrationality/T1|T1 · Irrationality established]]



## Node index

- [[note/sqrt-2-irrationality/H1|H1 · Assume rationality]]
- [[note/sqrt-2-irrationality/K1|K1 · Reduced fraction theorem]]
- [[note/sqrt-2-irrationality/K2|K2 · Parity of squares]]
- [[note/sqrt-2-irrationality/D1|D1 · Square root property]]
- [[note/sqrt-2-irrationality/R1|R1 · Reduced representation exists]]
- [[note/sqrt-2-irrationality/L1|L1 · Choose reduced witnesses]]
- [[note/sqrt-2-irrationality/R2|R2 · Witness conditions]]
- [[note/sqrt-2-irrationality/R3|R3 · Square relation]]
- [[note/sqrt-2-irrationality/R4|R4 · Even numerator]]
- [[note/sqrt-2-irrationality/R5|R5 · Even denominator square]]
- [[note/sqrt-2-irrationality/R6|R6 · Even denominator]]
- [[note/sqrt-2-irrationality/X1|X1 · Coprimality contradiction]]
- [[note/sqrt-2-irrationality/X2|X2 · Witness-free contradiction]]
- [[note/sqrt-2-irrationality/T1|T1 · Irrationality established]]
- [[note/sqrt-2-irrationality/C1|C1 · Normalize rationality]]
- [[note/sqrt-2-irrationality/C2|C2 · Square the representation]]
- [[note/sqrt-2-irrationality/C3|C3 · Infer numerator parity]]
- [[note/sqrt-2-irrationality/C4|C4 · Infer denominator square parity]]
- [[note/sqrt-2-irrationality/C5|C5 · Infer denominator parity]]
- [[note/sqrt-2-irrationality/C6|C6 · Expose the contradiction]]

## Explanatory edge index

- [[note/sqrt-2-irrationality/E4|E4 · Choose reduced witnesses]]
- [[note/sqrt-2-irrationality/E22|E22 · Close witness scope]]
- [[note/sqrt-2-irrationality/E23|E23 · Discharge rationality]]

## Personal notes
<!-- personal:start -->
<!-- personal:end -->
