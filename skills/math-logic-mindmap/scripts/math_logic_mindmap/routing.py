"""Deterministic downward orthogonal proof routing and geometry checks."""
from collections import defaultdict
import math
from pathlib import Path

from .common import Invalid, read_json, safe

ROUTING_PROFILE = "downward-orthogonal"
NODE_CLEARANCE = 24
PARALLEL_CLEARANCE = 32
PORT_GAP = 40
TURN_STUB = 32
NODE_GAP = 64
MIN_RANK_GAP = 56
AUTO_LAYER_GAP = 160
PROOF_ROUTING_FILES = ("manifest.json", "main.js", "geometry-core.cjs")
PROOF_ROUTING_SOURCE = "plugins/proof-routing"
PROOF_ROUTING_INSTALL = ".obsidian/plugins/proof-routing"


def proof_routing_sync_report(root):
    """Compare the readable Proof Routing source with its Obsidian install copy."""
    root = Path(root).resolve()
    source_missing = []
    missing = []
    different = []
    unchanged = []
    for name in PROOF_ROUTING_FILES:
        source = safe(root, f"{PROOF_ROUTING_SOURCE}/{name}")
        installed = safe(root, f"{PROOF_ROUTING_INSTALL}/{name}")
        if not source.is_file():
            source_missing.append(name)
        elif not installed.is_file():
            missing.append(name)
        elif source.read_bytes() != installed.read_bytes():
            different.append(name)
        else:
            unchanged.append(name)
    if source_missing:
        raise Invalid("PROOF-ROUTING-SOURCE: missing canonical files: " + ", ".join(source_missing))
    return {"status": "PASS" if not missing and not different else "FAIL",
            "missing": missing, "different": different, "unchanged": unchanged}


def sync_proof_routing(root, confirm=None):
    """Preview or explicitly copy canonical Proof Routing files into Obsidian."""
    root = Path(root).resolve()
    before = proof_routing_sync_report(root)
    result = {"action": "sync-proof-routing", "mode": "preview", **before,
              "confirmation": "--confirm proof-routing"}
    if confirm is None:
        return result
    if confirm != "proof-routing":
        raise Invalid("PROOF-ROUTING-CONFIRM: --confirm must exactly match proof-routing")
    for name in (*before["missing"], *before["different"]):
        source = safe(root, f"{PROOF_ROUTING_SOURCE}/{name}")
        installed = safe(root, f"{PROOF_ROUTING_INSTALL}/{name}")
        installed.parent.mkdir(parents=True, exist_ok=True)
        temporary = installed.with_name(installed.name + ".math-logic-mindmap-tmp")
        temporary.write_bytes(source.read_bytes())
        temporary.replace(installed)
    after = proof_routing_sync_report(root)
    return {"action": "sync-proof-routing", "mode": "confirmed", **after,
            "created": before["missing"], "overwritten": before["different"]}


def require_release_proof_routing_sync(root):
    """Reject a partial or stale install copy while preserving the no-plugin fallback."""
    root = Path(root).resolve()
    source_exists = [safe(root, f"{PROOF_ROUTING_SOURCE}/{name}").is_file()
                     for name in PROOF_ROUTING_FILES]
    installed_exists = [safe(root, f"{PROOF_ROUTING_INSTALL}/{name}").is_file()
                        for name in PROOF_ROUTING_FILES]
    if not any(source_exists) and not any(installed_exists):
        return {"status": "UNMANAGED"}
    if not all(source_exists):
        missing = [name for name, exists in zip(PROOF_ROUTING_FILES, source_exists) if not exists]
        raise Invalid("PROOF-ROUTING-SOURCE: missing canonical files: " + ", ".join(missing))
    report = proof_routing_sync_report(root)
    if len(report["missing"]) == len(PROOF_ROUTING_FILES) and not report["different"]:
        return {"status": "ABSENT"}
    if report["missing"] or report["different"]:
        parts = []
        if report["missing"]:
            parts.append("missing=" + ",".join(report["missing"]))
        if report["different"]:
            parts.append("different=" + ",".join(report["different"]))
        raise Invalid("PROOF-ROUTING-SYNC: " + "; ".join(parts))
    return report


def environment(root):
    manifest = root / ".obsidian/plugins/advanced-canvas/manifest.json"
    data = read_json(manifest) if manifest.exists() else {}
    return {"advanced_canvas": data.get("version"),
            "status": "INSTALLED" if data else "FALLBACK_TARGET"}


def _route_number(value):
    rounded = round(value, 2)
    return int(rounded) if rounded == int(rounded) else rounded


def active(canvas):
    return canvas.get("metadata", {}).get("proofRouting", {}).get("profile") == ROUTING_PROFILE


def _spread(count, width):
    if count <= 1:
        return [0.0]
    span = max(0.0, min(width / 2 - NODE_CLEARANCE, PORT_GAP * (count - 1) / 2))
    return [-span + 2 * span * i / (count - 1) for i in range(count)]


def prepare(canvas):
    """Set managed sides and recompute all route offsets deterministically."""
    canvas.setdefault("metadata", {})["proofRouting"] = {"profile": ROUTING_PROFILE}
    nodes = {n["id"]: n for n in canvas["nodes"] if n["type"] != "group"}
    incoming, outgoing = defaultdict(list), defaultdict(list)
    for edge in canvas["edges"]:
        edge["fromSide"], edge["toSide"] = "bottom", "top"
        edge.setdefault("styleAttributes", {})["pathfindingMethod"] = "square"
        edge["proofRoute"] = {}
        incoming[edge["toNode"]].append(edge)
        outgoing[edge["fromNode"]].append(edge)
    center = lambda n: n["x"] + n["width"] / 2
    for node_id, edges in incoming.items():
        ordered = sorted(edges, key=lambda e: (center(nodes[e["fromNode"]]), e["id"]))
        for edge, offset in zip(ordered, _spread(len(ordered), nodes[node_id]["width"])):
            edge["proofRoute"]["toOffset"] = _route_number(offset)
    for node_id, edges in outgoing.items():
        ordered = sorted(edges, key=lambda e: (center(nodes[e["toNode"]]), e["id"]))
        for edge, offset in zip(ordered, _spread(len(ordered), nodes[node_id]["width"])):
            edge["proofRoute"]["fromOffset"] = _route_number(offset)
    _allocate_middle_lanes(canvas, nodes)
    return canvas


def _allocate_middle_lanes(canvas, nodes):
    entries = []
    for edge in canvas["edges"]:
        spec = edge["proofRoute"]
        spec["midOffset"] = 0
        start = _port(nodes[edge["fromNode"]], "bottom", spec["fromOffset"])
        end = _port(nodes[edge["toNode"]], "top", spec["toOffset"])
        if abs(start[0] - end[0]) < 0.75:
            continue
        base = (start[1] + end[1]) / 2
        entries.append({"edge": edge, "start": start, "end": end, "base": base,
                        "left": min(start[0], end[0]), "right": max(start[0], end[0])})
    entries.sort(key=lambda item: (item["base"], item["edge"]["toNode"],
                                   item["start"][0], item["edge"]["id"]))
    assigned = []
    for item in entries:
        start, end, base = item["start"], item["end"], item["base"]
        lower, upper = start[1] + TURN_STUB, end[1] - TURN_STUB
        extent = max(1, math.ceil(max(base - lower, upper - base, 0) / PARALLEL_CLEARANCE))
        offsets = [0.0]
        for step in range(1, extent + 1):
            offsets.extend((-step * PARALLEL_CLEARANCE, step * PARALLEL_CLEARANCE))
        for offset in offsets:
            y = base + offset
            if y < lower or y > upper:
                continue
            segment = ((item["left"], y), (item["right"], y))
            if any(parallel_proximity(segment[0], segment[1], other["segment"][0], other["segment"][1])[0] > 1
                   and abs(y - other["y"]) < PARALLEL_CLEARANCE for other in assigned):
                continue
            if any(hits(segment[0], segment[1], node, NODE_CLEARANCE) for node in nodes.values()):
                continue
            item["edge"]["proofRoute"]["midOffset"] = _route_number(offset)
            assigned.append({"y": y, "segment": segment})
            break


def _port(node, side, offset=0.0):
    x, y, width, height = node["x"], node["y"], node["width"], node["height"]
    cx, cy = x + width / 2, y + height / 2
    if node.get("styleAttributes", {}).get("shape") == "circle" and side in ("top", "bottom"):
        radius = min(width, height) / 2
        offset = max(-radius + 5, min(radius - 5, offset))
        dy = math.sqrt(max(0, radius * radius - offset * offset))
        return (cx + offset, cy + (-dy if side == "top" else dy))
    if side == "top":
        return (cx + offset, y)
    if side == "bottom":
        return (cx + offset, y + height)
    if side == "left":
        return (x, cy + offset)
    return (x + width, cy + offset)


def route_points(canvas, edge):
    nodes = {n["id"]: n for n in canvas["nodes"] if n["type"] != "group"}
    spec = edge["proofRoute"]
    start = _port(nodes[edge["fromNode"]], "bottom", spec.get("fromOffset", 0))
    end = _port(nodes[edge["toNode"]], "top", spec.get("toOffset", 0))
    if abs(start[0] - end[0]) < 0.75:
        return [start, end]
    middle_y = (start[1] + end[1]) / 2 + spec.get("midOffset", 0)
    return [start, (start[0], middle_y), (end[0], middle_y), end]


def hits(a, b, node, pad=0):
    x, y, width, height = node["x"], node["y"], node["width"], node["height"]
    if node.get("styleAttributes", {}).get("shape") == "circle" and width == height:
        cx, cy = x + width / 2, y + height / 2
        px = min(max(cx, min(a[0], b[0])), max(a[0], b[0]))
        py = min(max(cy, min(a[1], b[1])), max(a[1], b[1]))
        return math.hypot(px - cx, py - cy) < width / 2 + pad - 0.001
    return ((a[0] == b[0] and x - pad < a[0] < x + width + pad
             and max(min(a[1], b[1]), y - pad) < min(max(a[1], b[1]), y + height + pad))
            or (a[1] == b[1] and y - pad < a[1] < y + height + pad
                and max(min(a[0], b[0]), x - pad) < min(max(a[0], b[0]), x + width + pad)))


def parallel_proximity(a, b, c, d):
    if a[0] == b[0] and c[0] == d[0]:
        overlap = min(max(a[1], b[1]), max(c[1], d[1])) - max(min(a[1], b[1]), min(c[1], d[1]))
        return max(0, overlap), abs(a[0] - c[0])
    if a[1] == b[1] and c[1] == d[1]:
        overlap = min(max(a[0], b[0]), max(c[0], d[0])) - max(min(a[0], b[0]), min(c[0], d[0]))
        return max(0, overlap), abs(a[1] - c[1])
    return 0, float("inf")


def _shared(a, b, c, d):
    vertical = a[0] == b[0] == c[0] == d[0]
    horizontal = a[1] == b[1] == c[1] == d[1]
    if not (vertical or horizontal):
        return 0
    axis = 1 if vertical else 0
    return max(0, min(max(a[axis], b[axis]), max(c[axis], d[axis]))
               - max(min(a[axis], b[axis]), min(c[axis], d[axis])))


def analyze(canvas):
    if not active(canvas):
        raise Invalid(f"ROUTE-PROFILE: requires {ROUTING_PROFILE}")
    nodes = {n["id"]: n for n in canvas["nodes"] if n["type"] != "group"}
    paths, conflicts, crossings, segments = {}, [], [], []
    for edge in canvas["edges"]:
        points = route_points(canvas, edge)
        paths[edge["id"]] = [[round(x, 2), round(y, 2)] for x, y in points]
        if points[-1][1] <= points[0][1]:
            conflicts.append({"code": "ROUTE-NOT-DOWNWARD", "edge": edge["id"]})
        if len(points) not in (2, 4):
            conflicts.append({"code": "ROUTE-BEND-COUNT", "edge": edge["id"]})
        for index, (a, b) in enumerate(zip(points, points[1:])):
            if a == b or (a[0] != b[0] and a[1] != b[1]):
                conflicts.append({"code": "ROUTE-NON-ORTHOGONAL", "edge": edge["id"]})
            if a[0] == b[0] and b[1] < a[1]:
                conflicts.append({"code": "ROUTE-LOCAL-NOT-DOWNWARD", "edge": edge["id"], "segment": index})
            if len(points) == 4 and index in (0, 2) and abs(b[1] - a[1]) < TURN_STUB:
                conflicts.append({"code": "ROUTE-TURN-CLEARANCE", "edge": edge["id"], "segment": index})
            segments.append((edge["id"], a, b))
            for node_id, node in nodes.items():
                if node_id == edge["fromNode"] and index == 0:
                    continue
                if node_id == edge["toNode"] and index == len(points) - 2:
                    continue
                if hits(a, b, node, 0):
                    conflicts.append({"code": "ROUTE-NODE-INTERSECTION", "edge": edge["id"], "node": node_id})
                elif hits(a, b, node, NODE_CLEARANCE):
                    conflicts.append({"code": "ROUTE-NODE-CLEARANCE", "edge": edge["id"], "node": node_id})
    for index, (edge_id, a, b) in enumerate(segments):
        for other_id, c, d in segments[index + 1:]:
            if edge_id == other_id:
                continue
            overlap = _shared(a, b, c, d)
            if overlap > 1:
                conflicts.append({"code": "ROUTE-SHARED-SEGMENT", "edge": edge_id,
                                  "other_edge": other_id, "length": round(overlap, 2)})
            else:
                projection, distance = parallel_proximity(a, b, c, d)
                if projection > 1 and 0 < distance < PARALLEL_CLEARANCE:
                    conflicts.append({"code": "ROUTE-PARALLEL-CLEARANCE", "edge": edge_id,
                                      "other_edge": other_id, "overlap": round(projection, 2),
                                      "distance": round(distance, 2)})
            if overlap <= 1 and a[0] == b[0] and c[1] == d[1] and min(c[0], d[0]) < a[0] < max(c[0], d[0]) and min(a[1], b[1]) < c[1] < max(a[1], b[1]):
                crossings.append([edge_id, other_id, [a[0], c[1]]])
            elif overlap <= 1 and a[1] == b[1] and c[0] == d[0] and min(a[0], b[0]) < c[0] < max(a[0], b[0]) and min(c[1], d[1]) < a[1] < max(c[1], d[1]):
                crossings.append([edge_id, other_id, [c[0], a[1]]])
    return {"identity": {"profile": ROUTING_PROFILE, "max_bends": 2}, "paths": paths,
            "conflicts": conflicts, "unknown_edges": [], "crossings": crossings,
            "status": "FAIL" if conflicts else "PASS", "visual": "UNREVIEWED"}


def require_clear(canvas, report=None):
    report = report or analyze(canvas)
    if report["status"] != "PASS":
        raise Invalid("ORTHOGONAL-ROUTING: " + str(report["conflicts"][:12]))
    return report
