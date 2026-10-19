import copy
import json
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from build import build, coverage_report, embedded_json, load_data, read_frontmatter, valid_url


def record(node_id="node-a", domain="government"):
    return {
        "id": node_id, "name": "Example institution", "name_zh": "示例机构",
        "category": "executive_agency", "jurisdiction": "US", "domain": domain,
        "official_url": "https://example.gov/", "website_type": "official",
        "function": "An example public function", "leader": None, "employee_count": None,
        "financial_profile": [], "publications": [], "parents": [],
        "sources": [{"url": "https://example.gov/about", "description": "Official overview"}],
        "verified_at": "2026-10-19", "verification_status": "partial",
    }


def relation(parent_id="node-b", relation_type="PART_OF"):
    return {"parent_id": parent_id, "type": relation_type, "evidence_url": "https://example.gov/structure"}


def financial_relation():
    edge = relation(relation_type="FINANCIALLY_DEPENDENT_ON")
    edge["funding_share"] = .6
    edge["periods"] = [
        {"year": year, "funding_share": .6, "numerator": 60, "denominator": 100,
         "currency": "USD", "scope": "operating_funding", "evidence_url": f"https://example.gov/report/{year}"}
        for year in (2024, 2025)
    ]
    return edge


class TemporaryAtlasTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.data_dir = self.root / "data" / "entities"
        self.web_dir = self.root / "web"
        self.web_dir.mkdir()
        (self.web_dir / "template.html").write_text(
            '<!doctype html><style>/*__INLINE_CSS__*/</style><script>const ATLAS_DATA = /*__EMBEDDED_DATA__*/;</script><script>/*__INLINE_JS__*/</script>',
            encoding="utf-8")
        (self.web_dir / "style.css").write_text("body { color: black; }", encoding="utf-8")
        (self.web_dir / "app.js").write_text("console.log(ATLAS_DATA);", encoding="utf-8")
        self.node = record()
        self.write(self.node)

    def write(self, value):
        path = self.data_dir / value["domain"] / f'{value["id"]}.md'
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("---\n" + yaml.safe_dump(value, allow_unicode=True, sort_keys=False) + "---\n\n# Notes\n", encoding="utf-8")
        return path

    def load(self):
        return load_data(self.data_dir, self.root)

    def graph_with_edge(self, edge):
        self.node["parents"] = [edge]
        self.write(self.node)
        self.write(record("node-b"))
        return self.load()

    def test_build_generates_json_coverage_and_offline_html(self):
        output = self.root / "dist"
        graph = build(self.data_dir, output, self.web_dir, self.root)
        self.assertEqual(json.loads((output / "atlas.json").read_text()), graph)
        self.assertEqual(json.loads((output / "coverage.json").read_text())["overall"]["total_entities"], 1)
        html = (output / "index.html").read_text()
        self.assertIn("const ATLAS_DATA =", html)
        self.assertNotIn('src="http', html)
        self.assertEqual(graph["entities"][0]["__file__"], "data/entities/government/node-a.md")
        self.assertFalse(graph["metadata"]["network_verification_performed"])

    def test_invalid_schema_fields_raise_useful_validation_errors(self):
        cases = [
            ("name", 7), ("name_zh", " "), ("domain", []), ("category", "not_a_category"),
            ("official_url", "http://example.gov"), ("website_type", "unlabeled_brand"),
            ("sources", {}), ("sources", []), ("sources", ["bad"]),
            ("sources", [{"url": "javascript:alert(1)"}]), ("parents", {}),
            ("parents", ["bad"]), ("parents", [{**relation(), "type": []}]),
            ("publications", [{"label": "News", "url": "http://example.gov/news"}]),
            ("publications", "bad"), ("financial_profile", None), ("aliases", "alias"),
            ("leader", []), ("leader", {"name": "Example", "title": "Chief", "status": []}),
            ("employee_count", {"value": True}), ("verification_status", "all_facts_verified"),
        ]
        for field, value in cases:
            with self.subTest(field=field, value=value):
                changed = copy.deepcopy(self.node)
                changed[field] = value
                # Non-string domains cannot determine a path, so keep its source location fixed.
                path = self.data_dir / "government" / "node-a.md"
                path.write_text("---\n" + yaml.safe_dump(changed) + "---\n", encoding="utf-8")
                with self.assertRaises(ValueError):
                    self.load()

    def test_dates_are_real_calendar_dates(self):
        for field, value in (("verified_at", "2026-02-30"), ("verified_at", "19/10/2026"), ("research_reviewed_at", "2026-13-01")):
            with self.subTest(field=field, value=value):
                changed = copy.deepcopy(self.node)
                changed[field] = value
                self.write(changed)
                with self.assertRaisesRegex(ValueError, "date"):
                    self.load()

    def test_unquoted_yaml_dates_are_normalized_for_json(self):
        self.node["verified_at"] = date(2026, 10, 19)
        self.node["research_reviewed_at"] = date(2026, 10, 18)
        self.write(self.node)
        graph = self.load()
        self.assertEqual(graph["entities"][0]["verified_at"], "2026-10-19")
        json.dumps(graph)

    def test_duplicate_yaml_keys_are_rejected(self):
        path = self.write(self.node)
        source = path.read_text().replace("name: Example institution", "name: First\nname: Second")
        path.write_text(source)
        with self.assertRaisesRegex(ValueError, "duplicate YAML key"):
            self.load()

    def test_empty_or_malformed_frontmatter_is_rejected(self):
        path = self.write(self.node)
        for source in ("# Missing frontmatter", "---\nname: Example\n", "---\n- list\n---\n"):
            with self.subTest(source=source):
                path.write_text(source)
                with self.assertRaises(ValueError):
                    self.load()

    def test_recursive_yaml_alias_is_rejected(self):
        path = self.write(self.node)
        path.write_text("---\nloop: &loop [*loop]\n---\n")
        with self.assertRaisesRegex(ValueError, "recursive YAML"):
            self.load()

    def test_non_finite_numbers_are_rejected(self):
        self.node["arbitrary_metadata"] = float("nan")
        self.write(self.node)
        with self.assertRaisesRegex(ValueError, "finite"):
            self.load()

    def test_filename_and_directory_must_match_record(self):
        path = self.write(self.node)
        path.rename(path.with_name("wrong-id.md"))
        with self.assertRaisesRegex(ValueError, "filename"):
            self.load()
        path.with_name("wrong-id.md").unlink()
        changed = record(domain="finance")
        self.write(changed)
        changed["domain"] = "government"
        (self.data_dir / "finance" / "node-a.md").write_text("---\n" + yaml.safe_dump(changed) + "---\n")
        with self.assertRaisesRegex(ValueError, "directory"):
            self.load()

    def test_duplicate_ids_across_domains_are_rejected(self):
        self.write(record(domain="finance"))
        with self.assertRaisesRegex(ValueError, "duplicate id"):
            self.load()

    def test_missing_parent_and_self_reference_are_rejected(self):
        self.node["parents"] = [relation()]
        self.write(self.node)
        with self.assertRaisesRegex(ValueError, "missing parent"):
            self.load()
        self.node["parents"] = [relation("node-a")]
        self.write(self.node)
        with self.assertRaisesRegex(ValueError, "self reference"):
            self.load()

    def test_duplicate_edges_are_rejected_but_distinct_types_are_allowed(self):
        self.node["parents"] = [relation(), relation()]
        self.write(self.node)
        self.write(record("node-b"))
        with self.assertRaisesRegex(ValueError, "duplicate relation"):
            self.load()
        self.node["parents"][1]["type"] = "REPORTS_TO"
        self.write(self.node)
        self.assertEqual(len(self.load()["edges"]), 2)

    def test_cycles_are_rejected_across_structural_relation_types(self):
        self.node["parents"] = [relation()]
        self.write(self.node)
        other = record("node-b")
        other["parents"] = [relation("node-a", "CONTROLLED_BY")]
        self.write(other)
        with self.assertRaisesRegex(ValueError, "Relation cycle"):
            self.load()

    def test_edge_temporal_and_extra_metadata_survives_export(self):
        edge = {**relation(), "valid_from": "2024-01-01", "valid_to": None,
                "observed_at": "2026-10-19", "source_published_at": "2024-01-01",
                "additional_evidence": [{"url": "https://example.gov/law"}]}
        exported = self.graph_with_edge(edge)["edges"][0]
        for key, value in edge.items():
            self.assertEqual(exported[key], value)
        self.assertEqual(exported["child_id"], "node-a")

    def test_edge_dates_and_derived_child_id_cannot_be_misrepresented(self):
        for changes in ({"valid_from": "2025-01-01", "valid_to": "2024-01-01"}, {"child_id": "spoofed"}):
            with self.subTest(changes=changes):
                with self.assertRaises(ValueError):
                    self.graph_with_edge({**relation(), **changes})

    def test_financial_dependency_keeps_per_period_evidence(self):
        edge = financial_relation()
        graph = self.graph_with_edge(edge)
        self.assertEqual(graph["edges"][0]["periods"], edge["periods"])
        self.assertEqual(graph["edges"][0]["funding_share"], .6)

    def test_financial_dependency_requires_comparable_consecutive_majority_years(self):
        cases = []
        edge = financial_relation(); edge["funding_share"] = .5; cases.append(edge)
        edge = financial_relation(); edge["funding_share"] = 1.1; cases.append(edge)
        edge = financial_relation(); edge["periods"] = ["2024", "2025"]; cases.append(edge)
        edge = financial_relation(); edge["periods"][1]["year"] = 2027; cases.append(edge)
        edge = financial_relation(); edge["periods"][1]["year"] = 2024; cases.append(edge)
        edge = financial_relation(); edge["periods"][1]["currency"] = "EUR"; cases.append(edge)
        edge = financial_relation(); edge["periods"][1]["scope"] = "contract_value"; cases.append(edge)
        edge = financial_relation(); edge["periods"][1]["funding_share"] = .5; cases.append(edge)
        edge = financial_relation(); edge["periods"][1]["numerator"] = 50; cases.append(edge)
        edge = financial_relation(); edge["periods"][1]["evidence_url"] = "http://example.gov"; cases.append(edge)
        for index, edge in enumerate(cases):
            with self.subTest(case=index):
                with self.assertRaises(ValueError):
                    self.graph_with_edge(edge)

    def test_reciprocal_funding_is_not_mistaken_for_a_hierarchy_cycle(self):
        self.graph_with_edge(financial_relation())
        other = record("node-b")
        edge = financial_relation()
        edge["parent_id"] = "node-a"
        other["parents"] = [edge]
        self.write(other)
        graph = self.load()
        self.assertEqual(coverage_report(graph)["overall"]["max_recorded_hierarchy_depth"], 0)

    def test_delegation_requires_described_scope(self):
        with self.assertRaisesRegex(ValueError, "scope"):
            self.graph_with_edge(relation(relation_type="FUNCTION_DELEGATED_BY"))

    def test_employee_count_requires_scope_period_and_numeric_count(self):
        base = {"value": 12, "unit": "employees", "period": "2025 annual report", "evidence_url": "https://example.gov/report"}
        for changes in ({"value": True}, {"value": "12"}, {"value": -1}, {"value": 12.2}, {"period": ""}, {"approximate": "true"}):
            with self.subTest(changes=changes):
                self.node["employee_count"] = {**base, **changes}
                self.write(self.node)
                with self.assertRaises(ValueError):
                    self.load()
        self.node["employee_count"] = base
        self.write(self.node)
        self.assertEqual(self.load()["entities"][0]["employee_count"]["value"], 12)

    def test_money_requires_financial_basis_and_documented_reporting_scope(self):
        base = {"metric": "net_income", "value": -10, "currency": "USD", "fiscal_year": 2025,
                "scope": "consolidated", "source_url": "https://example.gov/report", "source_date": "2026-01-01"}
        self.node["financial_profile"] = [base]
        self.write(self.node)
        self.assertEqual(self.load()["entities"][0]["financial_profile"][0]["value"], -10)
        for changes in ({"value": ""}, {"value": True}, {"metric": []}, {"metric": "money"}, {"scope": ""}, {"currency": "dollars"}, {"fiscal_year": "2025"}):
            with self.subTest(changes=changes):
                self.node["financial_profile"] = [{**base, **changes}]
                self.write(self.node)
                with self.assertRaises(ValueError):
                    self.load()

    def test_vacancy_is_distinct_from_unknown_leadership(self):
        self.node["leader"] = {"name": None, "title": "Director", "status": "vacant", "as_of": "2026-10-19", "evidence_url": "https://example.gov/leadership"}
        self.write(self.node)
        self.assertIsNone(self.load()["entities"][0]["leader"]["name"])
        self.node["leader"]["name"] = "Someone"
        self.write(self.node)
        with self.assertRaisesRegex(ValueError, "vacant"):
            self.load()

    def test_coverage_separates_inherited_declarations_from_recorded_review(self):
        other = record("node-b")
        other["research_reviewed_at"] = "2026-10-18"
        other["verification_status"] = "verified"
        self.write(other)
        report = coverage_report(self.load())
        self.assertEqual(report["overall"]["research_reviewed_entities"], 1)
        self.assertEqual(report["overall"]["inherited_entities"], 1)
        self.assertEqual(report["overall"]["source_declared_status_counts"], {"partial": 1, "verified": 1})
        self.assertEqual(report["overall"]["leader"]["missing_ids"], ["node-a", "node-b"])
        self.assertEqual(report["by_domain"]["finance"]["total_entities"], 0)
        self.assertFalse(report["network_verification_performed"])

    def test_embedded_data_cannot_close_script_or_become_html(self):
        payload = {"text": '</script><script>alert("x")</script>&\u2028\u2029'}
        encoded = embedded_json(payload)
        self.assertNotIn("<", encoded)
        self.assertNotIn(">", encoded)
        self.assertNotIn("&", encoded)
        self.assertNotIn("\u2028", encoded)
        self.assertNotIn("\u2029", encoded)
        self.assertEqual(json.loads(encoded), payload)
        self.node["function"] = payload["text"]
        self.write(self.node)
        output = self.root / "dist"
        build(self.data_dir, output, self.web_dir, self.root)
        self.assertEqual((output / "index.html").read_text().count("</script>"), 2)
        self.assertEqual(json.loads((output / "atlas.json").read_text())["entities"][0]["function"], payload["text"])

    def test_template_like_source_text_and_assets_are_left_intact(self):
        self.node["function"] = "Facts may contain /*__INLINE_JS__*/ or __EMBEDDED markers."
        self.write(self.node)
        (self.web_dir / "app.js").write_text('const marker = "/*__EMBEDDED_DATA__*/";')
        output = self.root / "dist"
        build(self.data_dir, output, self.web_dir, self.root)
        html = (output / "index.html").read_text()
        self.assertIn(self.node["function"], html)
        self.assertIn('const marker = "/*__EMBEDDED_DATA__*/";', html)

    def test_invalid_build_does_not_replace_last_good_output(self):
        output = self.root / "dist"
        build(self.data_dir, output, self.web_dir, self.root)
        before = {path.name: path.read_bytes() for path in output.iterdir()}
        self.node["sources"] = []
        self.write(self.node)
        with self.assertRaises(ValueError):
            build(self.data_dir, output, self.web_dir, self.root)
        self.assertEqual({path.name: path.read_bytes() for path in output.iterdir()}, before)
        self.write(record())
        (self.web_dir / "template.html").write_text("<html>missing markers</html>")
        with self.assertRaisesRegex(ValueError, "exactly one"):
            build(self.data_dir, output, self.web_dir, self.root)
        self.assertEqual({path.name: path.read_bytes() for path in output.iterdir()}, before)


class UrlTests(unittest.TestCase):
    def test_https_urls(self):
        for value in ("https://example.gov/", "https://example.gov:443/report?year=2025#table", "https://例子.中国/组织", "https://[2001:db8::1]/"):
            with self.subTest(value=value):
                self.assertTrue(valid_url(value))

    def test_invalid_and_unsafe_urls(self):
        for value in (None, [], "", "http://example.gov", "javascript:alert(1)", "//example.gov", "https:///missing", "https://user:secret@example.gov", "https://exa mple.gov", "https://example.gov/\npath", "https://example.gov\\@evil.gov", "https://example.gov:wrong", "https://example.gov:99999", "https://example.gov:", "https://-bad.gov", "https://example..gov", "https://example.gov/%ZZ", 'https://example.gov/<script>'):
            with self.subTest(value=value):
                self.assertFalse(valid_url(value))


class DatasetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.graph = load_data()
        cls.entities = {node["id"]: node for node in cls.graph["entities"]}

    def test_top_level_federal_branches_and_departments_remain_separate(self):
        self.assertEqual(sum(node["category"] == "executive_department" for node in self.entities.values()), 15)
        executive_id = "us-executive"
        self.assertNotIn(executive_id, {edge["parent_id"] for node_id in ("us-legislative", "us-judicial") for edge in self.entities[node_id]["parents"]})
        self.assertEqual(sum(node["category"] == "government_branch" for node in self.entities.values()), 3)

    def test_separate_sectors_do_not_invent_federal_control(self):
        for node_id in ("uc-system", "alphabet", "bofa-corp"):
            self.assertEqual(self.entities[node_id]["parents"], [])

    def test_all_edge_endpoints_and_source_links_are_valid(self):
        for edge in self.graph["edges"]:
            self.assertIn(edge["child_id"], self.entities)
            self.assertIn(edge["parent_id"], self.entities)
            self.assertTrue(valid_url(edge["evidence_url"]))
        self.assertEqual(len(self.graph["edges"]), sum(len(node["parents"]) for node in self.entities.values()))


if __name__ == "__main__":
    unittest.main()
