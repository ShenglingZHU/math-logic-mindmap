import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from math_logic_mindmap.common import Invalid
from math_logic_mindmap.routing import (NODE_CLEARANCE, PARALLEL_CLEARANCE, ROUTING_PROFILE,
                              PROOF_ROUTING_FILES, PROOF_ROUTING_INSTALL,
                              PROOF_ROUTING_SOURCE, _port, _route_number, analyze,
                              environment, hits, prepare, proof_routing_sync_report,
                              require_clear, require_release_proof_routing_sync,
                              route_points, sync_proof_routing)


class RoutingTests(unittest.TestCase):
    @staticmethod
    def seed_plugin_source(root):
        for name in PROOF_ROUTING_FILES:
            path = root / PROOF_ROUTING_SOURCE / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(("source:" + name + "\n").encode())

    def node_executable(self):
        executable = os.environ.get("MATH_LOGIC_MINDMAP_NODE") or shutil.which("node")
        if executable:
            return executable
        if os.environ.get("MATH_LOGIC_MINDMAP_REQUIRE_NODE") == "1":
            self.fail("Node is required because MATH_LOGIC_MINDMAP_REQUIRE_NODE=1")
        self.skipTest("Node is unavailable; set MATH_LOGIC_MINDMAP_NODE for plugin verification")

    @staticmethod
    def node(node_id, x, y, width=200, height=120, shape=None):
        node = {"id": node_id, "type": "text", "x": x, "y": y,
                "width": width, "height": height, "text": node_id}
        if shape:
            node["styleAttributes"] = {"shape": shape}
        return node

    def fixture(self, target_x=500):
        return prepare({"metadata": {}, "nodes": [self.node("A", 0, 0), self.node("B", target_x, 400)],
                        "edges": [{"id": "E1", "fromNode": "A", "toNode": "B"}]})

    def test_profile_and_route_numbers(self):
        canvas = self.fixture()
        self.assertEqual(canvas["metadata"]["proofRouting"]["profile"], ROUTING_PROFILE)
        self.assertEqual(_route_number(20.0), 20)
        self.assertEqual(_route_number(12.345), 12.35)
        canvas["metadata"]["proofRouting"]["profile"] = "unsupported-profile"
        with self.assertRaisesRegex(Invalid, "ROUTE-PROFILE"):
            analyze(canvas)

    def test_zero_and_two_bend_paths(self):
        aligned = self.fixture(0)
        self.assertEqual(len(route_points(aligned, aligned["edges"][0])), 2)
        offset = self.fixture()
        self.assertEqual(len(route_points(offset, offset["edges"][0])), 4)
        self.assertEqual(require_clear(offset)["status"], "PASS")

    def test_alignment_threshold(self):
        canvas = self.fixture(0)
        edge = canvas["edges"][0]
        for delta, length in ((0.74, 2), (0.75, 4), (0.76, 4)):
            canvas["nodes"][1]["x"] = delta
            self.assertEqual(len(route_points(canvas, edge)), length)

    def test_circle_port_clamps_positive_and_negative_offsets(self):
        circle = self.node("C", 0, 0, 100, 100, "circle")
        self.assertEqual(_port(circle, "top", 100)[0], 95)
        self.assertEqual(_port(circle, "top", -100)[0], 5)

    def test_positive_and_negative_middle_offsets(self):
        canvas = self.fixture()
        edge = canvas["edges"][0]
        base = route_points(canvas, edge)[1][1]
        for offset in (-32, 32):
            edge["proofRoute"]["midOffset"] = offset
            self.assertEqual(route_points(canvas, edge)[1][1], base + offset)

    def test_multiple_inputs_and_outputs_get_distinct_offsets(self):
        nodes = [self.node("A", -400, 0), self.node("B", 0, 0), self.node("C", 400, 0),
                 self.node("T", 0, 400), self.node("X", -250, 800), self.node("Y", 250, 800)]
        canvas = prepare({"metadata": {}, "nodes": nodes, "edges": [
            {"id": "E1", "fromNode": "A", "toNode": "T"},
            {"id": "E2", "fromNode": "B", "toNode": "T"},
            {"id": "E3", "fromNode": "C", "toNode": "T"},
            {"id": "E4", "fromNode": "T", "toNode": "X"},
            {"id": "E5", "fromNode": "T", "toNode": "Y"}]})
        self.assertEqual(sorted(e["proofRoute"]["toOffset"] for e in canvas["edges"][:3]), [-40, 0, 40])
        self.assertEqual(sorted(e["proofRoute"]["fromOffset"] for e in canvas["edges"][3:]), [-20, 20])

    def test_shape_intersection_and_clearance(self):
        node = {"x": 0, "y": 0, "width": 100, "height": 100,
                "styleAttributes": {"shape": "circle"}}
        self.assertFalse(hits((-10, -10), (10, -10), node))
        self.assertTrue(hits((-10, 50), (110, 50), node))
        self.assertEqual(NODE_CLEARANCE, 24)
        self.assertEqual(PARALLEL_CLEARANCE, 32)

    def test_environment_is_informational(self):
        with tempfile.TemporaryDirectory() as folder:
            self.assertEqual(environment(Path(folder))["status"], "FALLBACK_TARGET")

    def test_proof_routing_sync_previews_confirms_and_preserves_unknown_files(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.seed_plugin_source(root)
            before = sync_proof_routing(root)
            self.assertEqual(before["mode"], "preview")
            self.assertEqual(before["missing"], list(PROOF_ROUTING_FILES))
            self.assertFalse((root / PROOF_ROUTING_INSTALL).exists())

            unknown = root / PROOF_ROUTING_INSTALL / "debug.txt"
            unknown.parent.mkdir(parents=True)
            unknown.write_text("keep", encoding="utf-8")
            confirmed = sync_proof_routing(root, "proof-routing")
            self.assertEqual(confirmed["status"], "PASS")
            self.assertEqual(confirmed["created"], list(PROOF_ROUTING_FILES))
            self.assertEqual(unknown.read_text(encoding="utf-8"), "keep")

            repeated = sync_proof_routing(root, "proof-routing")
            self.assertEqual(repeated["created"], [])
            self.assertEqual(repeated["overwritten"], [])

    def test_proof_routing_sync_reports_difference_and_release_allows_absence(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.seed_plugin_source(root)
            self.assertEqual(require_release_proof_routing_sync(root)["status"], "ABSENT")
            sync_proof_routing(root, "proof-routing")
            installed = root / PROOF_ROUTING_INSTALL / "main.js"
            installed.write_text("local debugging change\n", encoding="utf-8")
            report = proof_routing_sync_report(root)
            self.assertEqual(report["different"], ["main.js"])
            with self.assertRaisesRegex(Invalid, "PROOF-ROUTING-SYNC"):
                require_release_proof_routing_sync(root)
            installed.unlink()
            with self.assertRaisesRegex(Invalid, "missing=main.js"):
                require_release_proof_routing_sync(root)

    def test_proof_routing_sync_requires_exact_confirmation(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.seed_plugin_source(root)
            with self.assertRaisesRegex(Invalid, "must exactly match proof-routing"):
                sync_proof_routing(root, "yes")

    def test_node_intersection_blocks(self):
        canvas = self.fixture()
        canvas["nodes"].append(self.node("X", 80, 180, 100, 100))
        with self.assertRaisesRegex(Invalid, "NODE-INTERSECTION"):
            require_clear(canvas)

    def test_python_and_plugin_geometry_match(self):
        executable = self.node_executable()
        root = Path(__file__).resolve().parents[1]
        core = root / "plugins/proof-routing/geometry-core.cjs"
        cases = []
        for shape in (None, "circle"):
            for target_x in (0, 0.74, 0.75, 500):
                canvas = self.fixture(target_x)
                if shape:
                    canvas["nodes"][0].update(width=100, height=100, styleAttributes={"shape": shape})
                    canvas["nodes"][1].update(width=100, height=100, styleAttributes={"shape": shape})
                for start_offset, end_offset, middle_offset in ((0, 0, 0), (100, -100, 32), (-30, 30, -32)):
                    canvas["edges"][0]["proofRoute"] = {"fromOffset": start_offset, "toOffset": end_offset,
                                                           "midOffset": middle_offset}
                    cases.append(json.loads(json.dumps(canvas)))
        expected = [[list(point) for point in route_points(canvas, canvas["edges"][0])] for canvas in cases]
        script = ("const fs=require('fs');const module={exports:{}};"
                  "new Function('module','exports',fs.readFileSync(process.argv[1],'utf8'))(module,module.exports);"
                  "const c=module.exports;const xs=JSON.parse(process.argv[2]);"
                  "console.log(JSON.stringify(xs.map(d=>c.points(d,d.edges[0]))));")
        actual = json.loads(subprocess.check_output(
            [executable, "-e", script, core.relative_to(root).as_posix(), json.dumps(cases)],
            cwd=root, text=True))
        self.assertEqual(actual, expected)

    def run_plugin_core(self, expression, payload):
        executable = self.node_executable()
        root = Path(__file__).resolve().parents[1]
        core = root / "plugins/proof-routing/geometry-core.cjs"
        script = ("const fs=require('fs');const module={exports:{}};"
                  "new Function('module','exports',fs.readFileSync(process.argv[1],'utf8'))(module,module.exports);"
                  "const c=module.exports;const input=JSON.parse(process.argv[2]);"
                  f"console.log(JSON.stringify({expression}));")
        return json.loads(subprocess.check_output(
            [executable, "-e", script, core.relative_to(root).as_posix(), json.dumps(payload)],
            cwd=root, text=True))

    def crossing_fixture(self, reverse=False, horizontal_first=True, vertical_x=200):
        horizontal_source_x, horizontal_target_x = ((0, 400) if not reverse else (400, 0))
        nodes = [self.node("HS", horizontal_source_x, 0, 100, 80),
                 self.node("HT", horizontal_target_x, 400, 100, 80),
                 self.node("VS", vertical_x, 0, 100, 80),
                 self.node("VT", vertical_x, 400, 100, 80)]
        horizontal = {"id": "H", "fromNode": "HS", "toNode": "HT"}
        vertical = {"id": "V", "fromNode": "VS", "toNode": "VT"}
        edges = [horizontal, vertical] if horizontal_first else [vertical, horizontal]
        return prepare({"metadata": {}, "nodes": nodes, "edges": edges})

    def test_plugin_horizontal_bridge_is_order_independent_and_directional(self):
        canvases = [self.crossing_fixture(False, True), self.crossing_fixture(False, False),
                    self.crossing_fixture(True, True), self.crossing_fixture(True, False)]
        actual = self.run_plugin_core(
            "input.map(canvas=>Object.fromEntries(c.routes(canvas).map(edge=>"
            "[edge.id,{bridges:edge.bridges,path:edge.path,crossings:edge.crossings.length}])))",
            canvases)
        for result in actual:
            self.assertEqual(len(result["H"]["bridges"]), 1)
            self.assertEqual(len(result["V"]["bridges"]), 0)
            self.assertEqual(result["H"]["crossings"], 1)
            self.assertEqual(result["V"]["crossings"], 1)
            self.assertIn(" A 8 8 ", result["H"]["path"])
            self.assertNotIn(" A ", result["V"]["path"])
        self.assertIn(" A 8 8 0 0 1 ", actual[0]["H"]["path"])
        self.assertIn(" A 8 8 0 0 0 ", actual[2]["H"]["path"])

    def test_plugin_crossing_boundaries_and_separate_bridges(self):
        route_sets = {
            "multiple": [{"id": "H", "points": [[0, 0], [0, 100], [100, 100], [100, 200]]},
                         {"id": "V1", "points": [[35, 0], [35, 200]]},
                         {"id": "V2", "points": [[70, 0], [70, 200]]}],
            "near_turn": [{"id": "H", "points": [[0, 0], [0, 100], [100, 100], [100, 200]]},
                          {"id": "V", "points": [[9, 0], [9, 200]]}],
            "at_turn": [{"id": "H", "points": [[0, 0], [0, 100], [100, 100], [100, 200]]},
                        {"id": "V", "points": [[0, 0], [0, 200]]}],
            "parallel": [{"id": "H1", "points": [[0, 100], [100, 100]]},
                         {"id": "H2", "points": [[0, 120], [100, 120]]}],
            "same_edge": [{"id": "E", "points": [[0, 0], [0, 100], [100, 100], [100, 200]]}],
        }
        expression = ("Object.fromEntries(Object.entries(input).map(([name,rs])=>{"
                      "const xs=c.detectCrossings(rs),bs=c.allocateBridges(rs,xs);"
                      "return [name,{crossings:xs.length,bridges:[...bs.entries()]}];})).valueOf()")
        actual = self.run_plugin_core(expression, route_sets)
        self.assertEqual(actual["multiple"]["crossings"], 2)
        multiple = dict(actual["multiple"]["bridges"])
        self.assertEqual([(bridge["startX"], bridge["endX"]) for bridge in multiple["H"]],
                         [(27, 43), (62, 78)])
        self.assertEqual(actual["near_turn"]["crossings"], 1)
        self.assertEqual(dict(actual["near_turn"]["bridges"])["H"], [])
        self.assertEqual(actual["at_turn"]["crossings"], 0)
        self.assertEqual(actual["parallel"]["crossings"], 0)
        self.assertEqual(actual["same_edge"]["crossings"], 0)

    def test_dense_crossings_merge_without_backtracking(self):
        route_sets = {
            "dense": [{"id": "H", "points": [[0, 50], [200, 50]]},
                      {"id": "V1", "points": [[100, 0], [100, 100]]},
                      {"id": "V2", "points": [[110, 0], [110, 100]]}],
            "boundary": [{"id": "H", "points": [[0, 50], [200, 50]]},
                         {"id": "V1", "points": [[100, 0], [100, 100]]},
                         {"id": "V2", "points": [[118, 0], [118, 100]]}],
        }
        expression = ("Object.fromEntries(Object.entries(input).map(([name,rs])=>{"
                      "const xs=c.detectCrossings(rs),bs=c.allocateBridges(rs,xs),h=rs[0];"
                      "return [name,{bridges:bs.get('H'),ltr:c.svg(h.points,bs.get('H')),"
                      "rtl:c.svg([[200,50],[0,50]],bs.get('H'))}];}))")
        actual = self.run_plugin_core(expression, route_sets)
        dense = actual["dense"]
        self.assertEqual(len(dense["bridges"]), 1)
        self.assertEqual((dense["bridges"][0]["startX"], dense["bridges"][0]["endX"]), (92, 118))
        self.assertEqual((dense["bridges"][0]["radiusX"], dense["bridges"][0]["radiusY"]), (13, 8))
        self.assertIn("L 92 50 A 13 8 0 0 1 118 50", dense["ltr"])
        self.assertIn("L 118 50 A 13 8 0 0 0 92 50", dense["rtl"])
        self.assertNotIn("L 102 50", dense["ltr"])
        boundary = actual["boundary"]["bridges"]
        self.assertEqual(len(boundary), 2)
        self.assertEqual(boundary[1]["startX"] - boundary[0]["endX"], 2)

    def test_global_label_avoidance_and_bridge_suppression(self):
        route_sets = {
            "room": [{"id": "U", "label": "upper", "points": [[0, 100], [200, 100]]},
                     {"id": "L", "points": [[0, 132], [200, 132]]},
                     {"id": "V", "points": [[100, 0], [100, 200]]}],
            "narrow": [{"id": "U", "label": "upper", "points": [[0, 100], [80, 100]]},
                       {"id": "L", "points": [[0, 132], [80, 132]]},
                       {"id": "V", "points": [[40, 0], [40, 200]]}],
            "vertical_label": [{"id": "H", "points": [[0, 100], [200, 100]]},
                               {"id": "V", "label": "vertical", "points": [[100, 0], [100, 200]]}],
        }
        expression = ("Object.fromEntries(Object.entries(input).map(([name,base])=>{"
                      "const xs=c.detectCrossings(base),bm=c.allocateBridges(base,xs);"
                      "const rs=base.map(e=>({...e,crossings:xs.filter(x=>x.edges.includes(e.id)),"
                      "bridges:bm.get(e.id),path:c.svg(e.points,bm.get(e.id))}));"
                      "const labeled=base.find(e=>e.label),out=c.resolveLabels(rs,[{edgeId:labeled.id,width:80}]);"
                      "const visible=out.routes.flatMap(e=>e.bridges);"
                      "return [name,{label:out.labels[0],suppressed:out.suppressed,"
                      "obscured:visible.filter(b=>c.bridgeIntersectsRect(b,out.labels[0].placement)).length,"
                      "routes:out.routes.map(e=>[e.id,e.crossings.length,e.bridges.length])}];}))")
        actual = self.run_plugin_core(expression, route_sets)
        room = actual["room"]
        self.assertEqual((room["label"]["placement"]["x"], room["label"]["placement"]["below"]),
                         (50, False))
        self.assertEqual(room["suppressed"], [])
        self.assertEqual(room["obscured"], 0)
        self.assertEqual(dict((edge, bridges) for edge, _, bridges in room["routes"]),
                         {"U": 1, "L": 1, "V": 0})
        narrow = actual["narrow"]
        self.assertEqual((narrow["label"]["placement"]["x"], narrow["label"]["placement"]["below"]),
                         (40, False))
        self.assertEqual(narrow["suppressed"], ["U:0:40:40"])
        self.assertEqual(narrow["obscured"], 0)
        routes = {edge: (crossings, bridges) for edge, crossings, bridges in narrow["routes"]}
        self.assertEqual(routes["U"], (1, 0))
        self.assertEqual(routes["L"], (1, 1))
        vertical = actual["vertical_label"]
        self.assertEqual(vertical["suppressed"], ["H:0:100:100"])
        self.assertEqual(vertical["obscured"], 0)
        vertical_routes = {edge: (crossings, bridges) for edge, crossings, bridges in vertical["routes"]}
        self.assertEqual(vertical_routes["H"], (1, 0))
        self.assertEqual(vertical_routes["V"], (1, 0))

    def test_plugin_and_python_crossing_sets_match(self):
        canvases = [self.crossing_fixture(reverse, horizontal_first)
                    for reverse in (False, True) for horizontal_first in (False, True)]
        offset = json.loads(json.dumps(self.crossing_fixture(False, True)))
        horizontal = next(edge for edge in offset["edges"] if edge["id"] == "H")
        horizontal["proofRoute"].update(fromOffset=20, toOffset=-20, midOffset=32)
        canvases.append(offset)
        circles = json.loads(json.dumps(self.crossing_fixture(True, False)))
        for node in circles["nodes"]:
            node["styleAttributes"] = {"shape": "circle"}
        canvases.append(circles)
        multi_nodes = [self.node("HS", 0, 0, 100, 80), self.node("HT", 400, 400, 100, 80),
                       self.node("V1S", 120, 0, 100, 80), self.node("V1T", 120, 400, 100, 80),
                       self.node("V2S", 280, 0, 100, 80), self.node("V2T", 280, 400, 100, 80)]
        canvases.append(prepare({"metadata": {}, "nodes": multi_nodes, "edges": [
            {"id": "H", "fromNode": "HS", "toNode": "HT"},
            {"id": "V1", "fromNode": "V1S", "toNode": "V1T"},
            {"id": "V2", "fromNode": "V2S", "toNode": "V2T"}]}))
        turn = self.crossing_fixture(False, True, vertical_x=0)
        canvases.append(turn)
        plugin = self.run_plugin_core(
            "input.map(canvas=>{const rs=canvas.edges.map(edge=>({...edge,points:c.points(canvas,edge)}));"
            "return c.detectCrossings(rs).map(x=>[x.edges,x.point]);})",
            canvases)
        for canvas, plugin_crossings in zip(canvases, plugin):
            python_crossings = analyze(canvas)["crossings"]
            normalize = lambda pair, point: (tuple(sorted(pair)), tuple(round(value, 8) for value in point))
            expected = sorted(normalize(item[:2], item[2]) for item in python_crossings)
            actual = sorted(normalize(item[0], item[1]) for item in plugin_crossings)
            self.assertEqual(actual, expected)

    def test_plugin_crossing_scan_handles_larger_graph(self):
        routes = []
        for index in range(50):
            routes.append({"id": f"H{index}", "points": [[0, index * 10], [1000, index * 10]]})
            routes.append({"id": f"V{index}", "points": [[index * 10 + 1, -10], [index * 10 + 1, 500]]})
        result = self.run_plugin_core(
            "(()=>{const start=performance.now(),xs=c.detectCrossings(input);"
            "const bridges=c.allocateBridges(input,xs);"
            "return {crossings:xs.length,bridges:[...bridges.values()].reduce((n,x)=>n+x.length,0),"
            "elapsed:performance.now()-start};})()", routes)
        self.assertEqual(result["crossings"], 2500)
        self.assertEqual(result["bridges"], 50)
        self.assertLess(result["elapsed"], 200)


if __name__ == "__main__":
    unittest.main()
