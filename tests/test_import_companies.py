import csv
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from import_companies import build_catalog, parse_file, primary_name


class CompanyImportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.source = Path(self.temp.name)

    def write_sources(self, nasdaq=None, other=None):
        rows = {
            "nasdaqlisted.txt": nasdaq or [{"Symbol": "AAPL", "Security Name": "Apple Inc. - Common Stock"}],
            "otherlisted.txt": other or [{"ACT Symbol": "DEMO", "Security Name": "Demo Corporation Common Stock", "Exchange": "N"}],
        }
        for filename, values in rows.items():
            fields = (["Symbol", "Security Name", "Market Category", "Test Issue", "Financial Status", "Round Lot Size", "ETF", "NextShares"]
                      if filename == "nasdaqlisted.txt" else ["ACT Symbol", "Security Name", "Exchange", "CQS Symbol", "ETF", "Round Lot Size", "Test Issue", "NASDAQ Symbol"])
            with (self.source / filename).open("w", newline="") as handle:
                writer = csv.DictWriter(handle, fields, delimiter="|")
                writer.writeheader()
                for value in values:
                    writer.writerow({**{key: "" for key in fields}, "ETF": "N", "Test Issue": "N", **value})
                handle.write("File Creation Time: 1023202621:31" + "|" * (len(fields) - 1) + "\n")

    def test_groups_share_classes_and_auxiliary_securities_without_new_orgs(self):
        self.write_sources(nasdaq=[
            {"Symbol": "GOOG", "Security Name": "Alphabet Inc. - Class C Capital Stock"},
            {"Symbol": "GOOGL", "Security Name": "Alphabet Inc. - Class A Common Stock"},
            {"Symbol": "GOOGM", "Security Name": "Alphabet Inc. - Depositary Shares representing Preferred Stock"},
        ])
        catalog, _ = build_catalog(self.source, "2026-10-24")
        alphabet = next(x for x in catalog["records"] if x["name"] == "Alphabet Inc.")
        self.assertEqual(alphabet["aliases"], ["GOOG", "GOOGL", "GOOGM"])
        self.assertEqual(alphabet["curated_id"], "alphabet")
        self.assertEqual(catalog["metadata"]["included_count"], 2)

    def test_etf_and_test_flags_take_priority_over_company_looking_names(self):
        self.write_sources(nasdaq=[
            {"Symbol": "AAPL", "Security Name": "Apple Inc. - Common Stock"},
            {"Symbol": "AAPX", "Security Name": "Apple Inc. fund", "ETF": "Y"},
            {"Symbol": "TEST", "Security Name": "Testing Corporation", "Test Issue": "Y", "ETF": "Y"},
        ])
        catalog, excluded = build_catalog(self.source, "2026-10-24")
        self.assertEqual({x["reason"] for x in excluded}, {"etf", "test_issue"})
        self.assertEqual(catalog["metadata"]["raw_count"], catalog["metadata"]["included_security_count"] + len(excluded))

    def test_auxiliary_subsidiary_is_not_attached_to_parent_name_prefix(self):
        self.write_sources(other=[
            {"ACT Symbol": "P", "Security Name": "Parent Corporation Common Stock", "Exchange": "N"},
            {"ACT Symbol": "PN", "Security Name": "Parent Corporation Finance LLC 5.00% Notes due 2030", "Exchange": "N"},
            {"ACT Symbol": "PP", "Security Name": "Parent Corporation 5.00% Preferred Stock", "Exchange": "N"},
        ])
        catalog, excluded = build_catalog(self.source, "2026-10-24")
        parent = next(x for x in catalog["records"] if x["name"] == "Parent Corporation")
        self.assertEqual(parent["aliases"], ["P", "PP"])
        self.assertEqual(excluded[0]["ticker"], "PN")

    def test_fund_name_does_not_merge_into_manager(self):
        self.write_sources(other=[
            {"ACT Symbol": "BLK", "Security Name": "BlackRock, Inc. Common Stock", "Exchange": "N"},
            {"ACT Symbol": "BHK", "Security Name": "BlackRock Core Bond Trust", "Exchange": "N"},
        ])
        catalog, _ = build_catalog(self.source, "2026-10-24")
        records = {x["name"]: x for x in catalog["records"]}
        self.assertIn("BlackRock Core Bond Trust", records)
        self.assertNotIn("curated_id", records["BlackRock Core Bond Trust"])
        self.assertEqual(records["BlackRock, Inc."]["curated_id"], "blackrock")

    def test_adr_and_preferred_security_descriptions_are_distinct(self):
        name, auxiliary = primary_name({"Security Name": "Example plc American Depositary Shares"}, "otherlisted.txt")
        self.assertEqual(name, "Example plc")
        self.assertFalse(auxiliary)
        _, auxiliary = primary_name({"Security Name": "Example plc Depositary Shares representing Preferred Series C"}, "otherlisted.txt")
        self.assertTrue(auxiliary)

    def test_missing_timestamp_or_unknown_flags_fail_instead_of_silent_truncation(self):
        self.write_sources()
        path = self.source / "nasdaqlisted.txt"
        path.write_text(path.read_text().split("File Creation Time:")[0])
        with self.assertRaisesRegex(ValueError, "timestamp"):
            parse_file(path)
        self.write_sources(nasdaq=[{"Symbol": "AAPL", "Security Name": "Apple Inc. - Common Stock", "ETF": "?"}])
        with self.assertRaisesRegex(ValueError, "Malformed"):
            build_catalog(self.source, "2026-10-24")

    def test_snapshot_is_reproducible_and_never_invents_cik_coordinates_or_homepage(self):
        saved = json.loads((ROOT / "data/catalogs/nasdaq.json").read_text())
        actual, excluded = build_catalog(ROOT / "data/sources/sec", saved["metadata"]["retrieved_at"])
        self.assertEqual(saved, actual)
        for source in actual["metadata"]["raw_files"]:
            self.assertEqual(hashlib.sha256((ROOT / source["path"]).read_bytes()).hexdigest(), source["sha256"])
        for record in actual["records"]:
            self.assertIsNone(record["official_url"])
            self.assertIsNone(record["location"])
            self.assertNotIn("cik", record["identifiers"])
            self.assertEqual(record["jurisdiction"], "US-listed")
        self.assertEqual(actual["metadata"]["raw_count"], actual["metadata"]["included_security_count"] + len(excluded))
        xom = next(x for x in actual["records"] if "XOM" in x["aliases"])
        self.assertNotIn("curated_id", xom)
        bac = next(x for x in actual["records"] if "BAC" in x["aliases"])
        self.assertEqual(bac["curated_id"], "bofa-corp")


if __name__ == "__main__":
    unittest.main()
