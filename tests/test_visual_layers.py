"""Keep map, events and monetary mechanisms separate from organizational control."""
import re
import shutil
import tempfile
import unittest
from pathlib import Path

import yaml

from test_build import ROOT, record
from build import coverage_report, embedded_json, load_data, load_geography, project_location


class VisualLayerTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.data_dir = self.root / "data" / "entities"
        self.node = record()
        self.write("entities/government", self.node)

    def write(self, folder, value):
        path = self.root / "data" / folder / (value["id"] + ".md")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("---\n" + yaml.safe_dump(value, allow_unicode=True) + "---\n", encoding="utf-8")
        return path

    def load(self):
        return load_data(self.data_dir, self.root)

    def event(self):
        return {"id": "event-example", "title": "Official announcement", "summary": "An official dated release.",
                "date": "2026-10-23", "entity_ids": ["node-a"], "category": "research",
                "source_url": "https://example.gov/news", "source_name": "Official newsroom", "reviewed_at": "2026-10-24"}

    def flow(self):
        return {"id": "flow-example", "source_id": "households", "target_id": "node-a", "label": "Taxes",
                "kind": "tax", "description": "Conceptual tax collection mechanism, not a measured transfer.",
                "evidence_url": "https://example.gov/taxes", "as_of": "2026-10-24", "basis": "mechanism", "amount": None}

    def test_absent_supplementary_folders_do_not_load_project_data(self):
        graph = self.load()
        self.assertEqual(graph["events"], [])
        self.assertEqual(graph["flows"], [])
        self.assertIsNone(graph["geography"])
        self.assertEqual(len(graph["entities"]), 1)

    def test_optional_profiles_are_exported_and_reported_without_inventing_a_leader(self):
        self.node.update({
            "location": {"lat": 38.9, "lon": -77.0, "city": "Washington", "state": "DC", "precision": "city", "evidence_url": "https://example.gov/contact"},
            "mission": "Public service", "ecosystem_role": "Provides the documented public service",
            "governance": {"apex": "Board", "mechanism": "Members vote under the charter", "evidence_url": "https://example.gov/charter"},
            "funding_model": {"summary": "Public appropriation", "inflows": ["Appropriations"], "outflows": ["Program operations"], "evidence_url": "https://example.gov/budget"},
        })
        self.write("entities/government", self.node)
        graph = self.load()
        self.assertIsNone(graph["entities"][0]["leader"])
        self.assertEqual(graph["entities"][0]["governance"], self.node["governance"])
        self.assertEqual(coverage_report(graph)["overall"]["location"]["recorded"], 1)

    def test_coordinates_reject_wrong_types_ranges_and_unsourced_precision(self):
        base = {"lat": 38.9, "lon": -77, "city": "Washington", "state": "DC", "precision": "city", "evidence_url": "https://example.gov/contact"}
        for changed in ({"lat": True}, {"lat": "38.9"}, {"lat": 91}, {"lon": -181}, {"lon": float("inf")}, {"lat": float("nan")}, {"precision": "exact"}, {"evidence_url": "http://example.gov/contact"}, {"city": ""}):
            with self.subTest(changed=changed):
                self.node["location"] = {**base, **changed}
                self.write("entities/government", self.node)
                with self.assertRaises(ValueError):
                    self.load()

    def test_governance_and_funding_require_actual_explanation_and_sources(self):
        cases = [
            ("mission", ""), ("ecosystem_role", 7),
            ("governance", {"apex": "Board", "mechanism": "", "evidence_url": "https://example.gov/charter"}),
            ("funding_model", {"summary": "Tuition", "inflows": "Tuition", "outflows": [], "evidence_url": "https://example.gov/budget"}),
            ("funding_model", {"summary": "Tuition", "inflows": [2], "outflows": [], "evidence_url": "https://example.gov/budget"}),
        ]
        for key, value in cases:
            with self.subTest(key=key, value=value):
                node = {**record(), key: value}
                self.write("entities/government", node)
                with self.assertRaises(ValueError):
                    self.load()

    def test_events_link_existing_organizations_and_keep_their_dates(self):
        event = self.event()
        event["scheduled_for"] = "2026-11-01"  # A future planned action is distinct from release date.
        self.write("events", event)
        graph = self.load()
        self.assertEqual(graph["events"][0]["scheduled_for"], "2026-11-01")
        self.assertEqual(graph["metadata"]["snapshot_date"], "2026-10-24")
        self.assertEqual(graph["edges"], [])
        self.assertFalse(graph["metadata"]["network_verification_performed"])

    def test_invalid_event_reference_date_url_and_future_release_are_rejected(self):
        for changed in ({"entity_ids": ["missing"]}, {"entity_ids": ["households"]}, {"entity_ids": []}, {"entity_ids": ["node-a", "node-a"]}, {"entity_ids": [["node-a"]]}, {"date": "2026-02-30"}, {"date": "2026-10-25"}, {"scheduled_for": "2026-02-30"}, {"source_url": "javascript:alert(1)"}, {"source_url": "https://user:secret@example.gov/"}):
            with self.subTest(changed=changed):
                self.write("events", {**self.event(), **changed})
                with self.assertRaises(ValueError):
                    self.load()

    def test_flow_mechanisms_never_become_strong_edges_or_measured_money(self):
        self.write("flows", self.flow())
        graph = self.load()
        self.assertEqual(graph["edges"], [])
        self.assertEqual(len(graph["flows"]), 1)
        self.assertIsNone(graph["flows"][0]["amount"])
        self.assertIn("households", {sector["id"] for sector in graph["sectors"]})
        self.assertNotIn("households", {entity["id"] for entity in graph["entities"]})

    def test_malicious_event_text_and_quoted_metadata_cannot_escape_embedded_script(self):
        event = self.event()
        event["title"] = '</script><img src=x onerror="alert(1)">'
        event["summary"] = '/*__INLINE_JS__*/\u2028 & <svg onload=alert(1)>'
        self.write("events", event)
        graph = self.load()
        payload = embedded_json(graph)
        self.assertNotIn("</script>", payload)
        self.assertNotIn("<img", payload)
        self.assertNotIn("<svg", payload)
        self.assertNotIn("\u2028", payload)
        self.assertEqual(graph["events"][0]["title"], event["title"])

    def test_invalid_flow_endpoints_amounts_and_dates_are_rejected(self):
        for changed in ({"source_id": "missing"}, {"target_id": "households"}, {"amount": 1}, {"amount": "unknown"}, {"amount": False}, {"basis": "estimated"}, {"as_of": "2026-13-01"}, {"evidence_url": "http://example.gov"}):
            with self.subTest(changed=changed):
                self.write("flows", {**self.flow(), **changed})
                with self.assertRaises(ValueError):
                    self.load()
        flow = self.flow()
        del flow["amount"]
        self.write("flows", flow)
        with self.assertRaisesRegex(ValueError, "amount"):
            self.load()

    def test_duplicate_records_and_duplicate_flow_mechanisms_are_rejected(self):
        self.write("events", self.event())
        duplicate = self.write("events/nested", self.event())
        with self.assertRaisesRegex(ValueError, "duplicate id"):
            self.load()
        duplicate.unlink()
        self.write("flows", self.flow())
        self.write("flows", {**self.flow(), "id": "another-flow"})
        with self.assertRaisesRegex(ValueError, "duplicate flow"):
            self.load()

    def test_conceptual_sector_ids_cannot_masquerade_as_organizations(self):
        self.write("entities/government", record("households"))
        with self.assertRaisesRegex(ValueError, "duplicate identifiers"):
            self.load()


class GeographyTests(unittest.TestCase):
    def test_vendored_map_is_real_50_state_geometry_and_dc_with_separate_insets(self):
        geography = load_geography(ROOT / "data" / "geography", ROOT)
        self.assertEqual(len(geography["states"]), 51)
        states = {state["id"]: state for state in geography["states"]}
        self.assertEqual(states["02"]["region"], "alaska")
        self.assertEqual(states["15"]["region"], "hawaii")
        self.assertEqual(states["11"]["name"], "District of Columbia")
        for state in states.values():
            self.assertRegex(state["path"], r"^M[-\d.,MLZ]+Z$")
            coordinates = [float(value) for value in re.findall(r"-?\d+\.\d+", state["path"])]
            self.assertTrue(all(-1 <= x <= 1001 for x in coordinates[::2]))
            self.assertTrue(all(-1 <= y <= 601 for y in coordinates[1::2]))
        self.assertIn("2017", geography["dataset"])
        self.assertEqual(geography["license"], "ISC")

    def test_marker_projection_agrees_with_boundary_projection_and_dateline_inset(self):
        self.assertEqual(project_location(-125, 50), (0, 0))
        self.assertEqual(project_location(-66, 24), (1000, 600))
        self.assertEqual(project_location(175, 60, "alaska"), project_location(-185, 60, "alaska"))
        x, y = project_location(-157.86, 21.31, "hawaii")
        self.assertTrue(285 < x < 415 and 490 < y < 575)

    def test_unreviewed_map_changes_fail_checksum_validation(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary) / "geography"
            shutil.copytree(ROOT / "data" / "geography", directory)
            source = directory / "states-10m.topo.json"
            source.write_bytes(source.read_bytes() + b" ")
            with self.assertRaisesRegex(ValueError, "checksum"):
                load_geography(directory, Path(temporary))


if __name__ == "__main__":
    unittest.main()
