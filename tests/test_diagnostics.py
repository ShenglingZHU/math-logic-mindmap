import unittest

from math_logic_mindmap.diagnostics import summarize
from math_logic_mindmap.routing import prepare


class DiagnosticTests(unittest.TestCase):
    def test_route_summary_and_port_loads(self):
        node = lambda node_id, x, y: {"id": node_id, "type": "text", "x": x, "y": y,
                                           "width": 100, "height": 80, "text": node_id}
        canvas = prepare({"metadata": {}, "nodes": [node("A", 0, 0), node("B", 300, 400)],
                          "edges": [{"id": "E1", "fromNode": "A", "toNode": "B"}]})
        report = summarize(canvas)
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["route_summary"]["max_bends"], 2)
        self.assertEqual(report["port_collisions"], [])
        self.assertEqual(len(report["port_loads"]), 2)
        self.assertEqual(report["crossing_count"], 0)

    def test_only_identical_offsets_are_port_collisions(self):
        node = lambda node_id, x, y: {"id": node_id, "type": "text", "x": x, "y": y,
                                      "width": 180, "height": 120, "text": node_id}
        canvas = prepare({"metadata": {}, "nodes": [node("A", -300, 0), node("B", 300, 0), node("T", 0, 400)],
                          "edges": [{"id": "E1", "fromNode": "A", "toNode": "T"},
                                    {"id": "E2", "fromNode": "B", "toNode": "T"}]})
        self.assertEqual(summarize(canvas)["port_collisions"], [])
        canvas["edges"][1]["proofRoute"]["toOffset"] = canvas["edges"][0]["proofRoute"]["toOffset"]
        self.assertEqual(summarize(canvas)["port_collisions"][0]["edges"], ["E1", "E2"])


if __name__ == "__main__":
    unittest.main()
