# Proof Architectures — Guidance, Not Templates

The purpose of this file is to recognize real proof obligations. Never make every proof look like one of these shapes. Build the proof first; select or combine architectures afterward.

## Direct implication
For `A ⇒ B`, roots may include `A` plus definitions/tools. The target is `B`. Intermediate lemmas appear where actual dependencies merge.

## Biconditional / equivalence
Usually requires two semantically independent obligations:
- path 1 proves `A ⇒ B`;
- path 2 proves `B ⇒ A`;
- the two completed directions enter a `COMBINE` node, whose single successor is the `A ⇔ B` result.

Do not represent only one direction.

## Mathematical induction
Introduce an arbitrary induction parameter with `LOCAL_INTRODUCTION`, then state only the induction proposition in a same-scope `HYPOTHESIS_LOCAL`. Close that scope with an `induction_generalization` DISCHARGES edge naming both the generalized parameter and discharged hypothesis. An induction COMBINE records base IDs, a nonempty list of directly discharged step IDs, and the induction-principle ID, and produces an independent result. Multiple constructor steps each close their own induction scope and directly feed the final COMBINE. Strong induction states the full earlier-index hypothesis; if its base is the vacuous part of the step, record that explicitly instead of inventing a base fact. Structural induction records constructor coverage in its principle and proves every constructor step. Check the base index, prohibition on using the desired successor, and the exact strong-induction range by mathematical review.

## Contradiction
Typical logic:
- desired claim `P`;
- local assumption `¬P`;
- dependencies under that assumption;
- explicit contradiction node;
- discharge of `¬P`;
- target `P`.

The contradiction must be explicit, not merely “this is impossible”.
To prove a universal claim by contradiction for an arbitrary object, open an outer scope with an arbitrary `LOCAL_INTRODUCTION`. Open an inner scope at a root `HYPOTHESIS_LOCAL` stating the negated instance, derive a `CONTRADICTION`, and close that inner scope with `reductio`. Close the outer scope separately with `universal_generalization`. The inner root may use the outer scope's introduced variable through its declared `parent_scope`.

For a universal conditional claim, use the same two scopes: the inner root states the antecedent, `conditional_proof` closes it after the consequent is established, and the outer `universal_generalization` closes the arbitrary-variable scope. Each closing edge names only the logical rule it performs.

## Contrapositive
For `A ⇒ B`, a path may target `¬B ⇒ ¬A`. Make the equivalence of implication and contrapositive explicit as a logical tool when pedagogically useful.

## Case analysis
Feed a proved partition or coverage result into one circular `CASE`. Its EDGE_DETAIL outputs state the cases in short natural-language labels and enter substantive rectangles carrying the exact conditions. At least two branches are required in finite mode; every branch conclusion enters the explicitly paired case-reconciliation COMBINE. The COMBINE records one `case_closures` row per branch, discharging each finite case condition. A nontrivial exhaustiveness argument is an independent input result, while the CASE note explains its application and any relevant disjointness. For an indexed family, use exactly one arbitrary-index branch starting with `LOCAL_INTRODUCTION`; its conclusion and the coverage input enter the paired COMBINE, which records index generalization in both its branch closure and local-scope closure. Ordinary universal introduction without an indexed partition uses no CASE.

## Existence / construction
Show:
- construction/witness choice;
- every required property verification, potentially in parallel;
- route the verified properties through a `COMBINE` node to produce “witness satisfies all conditions”;
- existence target.

For uniqueness, add a separate path: assume two candidates, prove equality, then route existence + uniqueness through a `COMBINE` node before the final existence-and-uniqueness result.
For constructive existence, record the new object's definition, dependencies on already introduced variables, well-definedness, and domain check in `CONSTRUCTION` or `EXISTENCE_WITNESS`. Verify the predicate before an explanatory existential-introduction edge yields the existential conclusion. For existential elimination, enter a witness-mode `LOCAL_INTRODUCTION` from an existing existential result, use its local fact, then close with `existential_elimination`; the fresh witness must not remain free in the outside conclusion. For uniqueness, introduce two arbitrary candidates in one local scope, prove equality, and combine that conclusion with existence. Nonconstructive existence by contradiction, compactness, or choice follows the actual logical/theorem dependencies and does not invent a constructed witness.

## Upper/lower bounds and squeeze
Lower-bound and upper-bound paths may be independent. When the pair jointly yields the equality/limit/optimal value, route both bounds through a `COMBINE` node before that result. State equality conditions when they matter.

## Optimization
Distinguish:
- feasibility/domain/regularity;
- necessary conditions (e.g. first-order condition);
- candidate solution;
- sufficient condition/global optimality proof (convexity, second-order conditions, comparison, KKT sufficiency, etc.);
- uniqueness if claimed.

Never infer global optimality from a stationary point unless justified.

## Inequalities
Often useful structure:
- admissible domain/sign conditions;
- transformation/normalization;
- the invoked theorem as a `KNOWN_RESULT` with visible `FLOW`;
- verification of its hypotheses in nodes or complete local derivation steps, with independent branches converging through `COMBINE`;
- equality condition path if relevant;
- target inequality.

## Limits / analysis
Separate:
- convergence/integrability/measurability/dominating assumptions;
- theorem enabling exchange of limit/integral/expectation/sum;
- local limit calculation;
- final exchange/limit result.

For epsilon-delta proofs, the choice of `δ(ε)` is usually a construction node and the verification path should be explicit.

## Linear algebra
Common obligations include dimensions, rank/subspace membership, orthogonality, invertibility, eigenvalue hypotheses, basis assumptions, and use of spectral/rank-nullity facts. Make dimension compatibility visible when it is essential.

## Probability
Expose conditioning events with nonzero probability, sigma-algebra/measurability conditions when material, independence assumptions, law-of-total-probability partitions, and integrability/finite expectation assumptions as needed.

## Set equality
A robust proof often has two inclusion branches `A⊆B` and `B⊆A` feeding a `COMBINE` node whose successor is `A=B`. For function equality, analogous pointwise equality obligations may replace set inclusion.

## “If and only if” with many characterizations
For equivalences `A⇔B⇔C...`, do not mechanically prove every pair. Build the minimal directed implication network actually used (e.g. cycle `A⇒B⇒C⇒A`) and make the global equivalence conclusion depend on that completed network.

## Algebraic identity
An identity may be a linear derivation if every step truly depends on the previous expression; do not artificially add branches. If the identity relies on independent lemmas (e.g. factorization + domain condition), expose those as side inputs.

## Proof by invariant / extremal principle
Expose:
- invariant/extremal object definition;
- preservation or extremality proof;
- consequence of the invariant/extreme choice;
- target.

## Pigeonhole / counting
Show the objects, boxes/categories, counting bound, and the exact inequality that triggers the pigeonhole conclusion. Avoid collapsing the key count into “by pigeonhole”.

## Diagonalization / fixed-point / compactness arguments
These often require multiple technical condition branches. Keep compactness/completeness/continuity/closedness assumptions visible where they enable extraction, convergence, or fixed-point results.

## Alternative proofs
When the user benefits from alternatives, do **not** merge unrelated proof methods into one strict DAG. Use separate slug-suffixed Canvas/models with their own roots and target, so dependencies remain auditable.


## Multi-input convergence rule
Across every proof architecture above, any strict result with two or more logical predecessors must be preceded by a `COMBINE` node. The pattern descriptions never authorize direct multi-parent arrows into an ordinary result node. A reader-visible one-input elementary operation may use `TRANSFORM` only after all applicability conditions are present in that input context.

## DAG vs implication cycle
A cycle among abstract propositions used to prove equivalence is not a cycle of proof steps.
Model each established directed implication as a distinct result node; COMBINE those results
into the equivalence target. Never put A→B→C→A as a directed cycle in the Proof DAG itself.
Groups show nested local scopes; CASE/COMBINE pairs show case boundaries. Neither a group nor a layout position discharges a hypothesis.
