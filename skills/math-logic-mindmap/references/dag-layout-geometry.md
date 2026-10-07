# Canvas Geometry and Downward Orthogonal Routing

## Layered layout

Lay out the graph only after mathematical dependencies are stable. Direction is fixed at top → bottom. A strict target must be below its sources, cards must not overlap, and the endpoint rectangles of a logical edge must have at least 56 px of vertical clearance. Automatic layout leaves at least 64 px between nodes in one rank and normally at least 160 px between ranks, increasing it when parallel horizontal segments require more space. Place external theorems and branch results near their first use; not every strict root must occupy the first row.

Keep the main proof chain central, continuous, and easy to follow, but allow small horizontal shifts at individual ranks to avoid real routing conflicts; do not force the entire spine to share one x-coordinate. Each COMBINE is the soft center of a local cluster, with inputs arranged around it at the nearest legal positions above. Long-range reuse may cross ranks, but never duplicate a conclusion, create a mathematical node, expand an outer corridor, or change proof structure merely to shorten a route.

## `downward-orthogonal`

Every edge normally leaves the bottom of its source and enters the top of its target:

- If the port x-coordinates are effectively aligned, use one vertical line.
- Otherwise, generate vertical → horizontal → vertical segments around the midpoint of the port y-coordinates; crowded horizontal segments may be separated with `proofRoute.midOffset`.
- Remove duplicate points and redundant collinear points, so an edge has zero or two bends.
- Every local segment remains downward or horizontal; never create upward backtracking.
- A horizontal segment stays within the horizontal span between its source and target ports.

Sort multiple COMBINE inputs at the top by source x-coordinate and ordinary multiple outputs at the bottom by target x-coordinate. The normal expected port spacing is 40 px. Deterministically separate horizontal segments by 32 px center-to-center, and keep the first and last vertical segments at least 32 px long. Offsets distinguish arrows only; they do not extend into independent corridors. TRANSFORM's single input and output are centered by default.

## Readability tradeoffs

An ordinary, isolated crossing between arrows is legal: count it, but do not block build or release. When the choice is between a crossing and a distant detour, choose the crossing. Active Proof Routing follows a fixed rule for ordinary crossings strictly inside horizontal and vertical segments: the horizontal line bridges over the vertical line with an upward arc of 8 px vertical radius, independent of edge-array or drawing order. Merge intersections less than 18 px apart into one fixed-height elliptical bridge, retaining at least 2 px of straight line between bridges. If an intersection is less than 10 px from a horizontal bend, keep a straight line rather than collapsing it into an illegible tiny arc. Endpoint and bend contacts are not ordinary crossings.

The following conditions block release:

- A route passes through the body of an unrelated node.
- A route comes within 24 px of an unrelated node, or projected parallel segments that overlap by more than 1 px have centerlines less than 32 px apart.
- Two edges with different meanings share more than 1 px of collinear segment.
- A route is not orthogonal, flows upward, or has a bend count other than zero or two.
- Node rectangles overlap, an endpoint is missing, or an arrow points the wrong way.

Resolve conflicts only by changing ranks, within-rank order, horizontal branch positions, and first-use positions of supporting theorems. Never add more than two bends, route around the outer edge of the Canvas, or create fact packages or forwarding nodes.

Automatic layout first eliminates card intersections and long collinear overlaps using actual `downward-orthogonal` routes, then optimizes COMBINE input distance, cluster-center deviation, total route length, ordinary crossings, and Canvas width. Clustering metrics are soft objectives, not independent release gates. A manually imported layout still takes precedence over automatic coordinates.

## Advanced Canvas fallback

The Proof Routing installation copy reads `metadata.proofRouting.profile="downward-orthogonal"` and each edge's `proofRoute.fromOffset/toOffset/midOffset`, then recomputes bends and crossing arcs from current node positions. Bends and arcs are derived display data and are written to neither Canvas nor manifest. The plugin first measures labels, then places each label centered above, centered below, or at the nearest shifted position on its owning horizontal segment while considering all arcs. If no legal position exists, suppress the bridge obscured by that label. Draw all edges first and labels afterward in one top layer; general label-to-label collision layout is not handled.

Without the adapter, edges retain Advanced Canvas `square` as a readable, editable fallback. Plugin load state, DOM sampling, save/reopen checks, and runtime hashes are not release gates.
