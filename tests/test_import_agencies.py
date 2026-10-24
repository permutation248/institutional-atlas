"""Meaningful parser, provenance and identity guarantees for the public catalogs."""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("import_agencies", ROOT / "scripts/import_agencies.py")
agencies = importlib.util.module_from_spec(spec)
spec.loader.exec_module(agencies)


class AgencyImportTests(unittest.TestCase):
    def test_directory_mark_up_and_html_entities(self):
        raw = '''<h2 class="usa-accordion__heading"><button data-agency-name="dr-Test" data-node-id="12">Test &amp; Agency (TA)</button></h2>
        <div class="usa-accordion__content usa-prose"><p>Handles &lt;public&gt; information.</p>
        <p class="field--name-field-website"><a href="https://example.gov/">Official</a></p>
        <p class="field--name-field-more-information"><a href="/agencies/test">More information</a></p></div>'''
        record = agencies.parse_usagov(raw)[0]
        self.assertEqual(record["name"], "Test & Agency (TA)")
        self.assertEqual(record["url"], "https://www.usa.gov/agencies/test")
        self.assertEqual(record["description"], "Handles <public> information.")

    def test_empty_or_changed_directory_is_not_silently_successful(self):
        with self.assertRaises(ValueError):
            agencies.parse_usagov("<html>maintenance</html>")
        with self.assertRaises(ValueError):
            agencies.parse_usagov('<h2 class="usa-accordion__heading"><button>Unknown</button>')

    def test_only_known_https_is_an_official_link(self):
        self.assertIsNone(agencies.https_url("http://example.gov/"))
        self.assertIsNone(agencies.https_url("javascript:alert(1)"))
        self.assertIsNone(agencies.https_url("https://user:pass@example.gov/"))
        self.assertEqual(agencies.https_url("https://example.gov/"), "https://example.gov/")

    def test_name_matching_is_order_tolerant_not_fuzzy(self):
        self.assertEqual(agencies.name_key("Department of Agriculture"), agencies.name_key("Agriculture Department"))
        self.assertEqual(agencies.name_key("Centers for Medicare & Medicaid Services (CMS)"), agencies.name_key("Centers for Medicare and Medicaid Services"))
        self.assertNotEqual(agencies.name_key("Department of Education"), agencies.name_key("Education Office"))

    def test_duplicate_fr_identity_fails(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            (directory / "retrieval.json").write_text(json.dumps({"retrieved_at": "2026-10-24", "sources": []}))
            (directory / "federal-register-agencies.json").write_text(json.dumps([{"id": 99, "name": "Test", "url": "https://example.gov/"}] * 2))
            with self.assertRaisesRegex(ValueError, "duplicate or invalid"):
                agencies.build_catalog(directory, directory / "entities")

    def test_complete_snapshot_count_identity_and_non_hierarchy_contract(self):
        result = agencies.build_catalog()
        meta, records = result["metadata"], result["records"]
        self.assertEqual(meta["raw_count"], meta["included_count"] + meta["duplicate_count"] + meta["excluded_count"])
        self.assertEqual(len(records), len({r["id"] for r in records}))
        self.assertEqual(meta["usagov_pages"], 22)
        self.assertGreater(meta["federal_register_count"], 450)
        self.assertGreater(meta["usagov_count"], 400)
        self.assertTrue(all("parents" not in r and r["location"] is None for r in records))
        self.assertEqual(next(r for r in records if r["id"] == "fr-502")["curated_id"], "us-house")
        self.assertTrue(any(r["id"] == "fr-557" and r["source_fields"]["current_status"] == "not_verified_includes_historical" for r in records))


if __name__ == "__main__":
    unittest.main()
