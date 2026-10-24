"""Semantic checks for a reproducible full-directory import, with tiny fixtures."""
import csv
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("import_colleges", ROOT / "scripts" / "import_colleges.py")
COLLEGES = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(COLLEGES)


def fixture(**updates):
    result = {key: "" for key in COLLEGES.REQUIRED}
    result.update(UNITID="123456", INSTNM="Example College", STABBR="CA", CITY="Example City", WEBADDR="https://college.example.edu/", SECTOR="2", ICLEVEL="1", CONTROL="2", DEGGRANT="1", ACT="A", CYACTIVE="1", CLOSEDAT="-2", LATITUDE="37.4", LONGITUD="-122.1")
    result.update(updates)
    return result


class CollegeImportTests(unittest.TestCase):
    def test_closed_in_current_year_is_not_current_open_campus(self):
        self.assertEqual(COLLEGES.exclusion_reason(fixture(ACT="M")), "not_open_in_source_period")

    def test_non_degree_school_is_included_and_explicitly_labeled(self):
        row = fixture(SECTOR="9", DEGGRANT="2", ICLEVEL="3", CONTROL="3")
        self.assertIsNone(COLLEGES.exclusion_reason(row))
        self.assertIn("非学位", COLLEGES.record(row)["institution_type"])

    def test_territory_and_administrative_unit_are_distinct_exclusions(self):
        self.assertEqual(COLLEGES.exclusion_reason(fixture(STABBR="PR")), "outside_50_states_dc")
        self.assertEqual(COLLEGES.exclusion_reason(fixture(SECTOR="0")), "administrative_or_unknown_sector")

    def test_https_is_never_assumed_from_http_or_unqualified_host(self):
        self.assertIsNone(COLLEGES.website(fixture(WEBADDR="http://college.example.edu"))[0])
        self.assertIsNone(COLLEGES.website(fixture(WEBADDR="college.example.edu"))[0])
        self.assertIsNone(COLLEGES.website(fixture(WEBADDR="https://user:pass@college.example.edu"))[0])

    def test_bare_host_requires_same_host_https_evidence(self):
        row = fixture(WEBADDR="college.example.edu/", ADMINURL="https://admissions.other.edu/")
        self.assertIsNone(COLLEGES.website(row)[0])
        row["ADMINURL"] = "https://college.example.edu/admissions"
        item = COLLEGES.record(row)
        self.assertEqual(item["official_url"], "https://college.example.edu/")
        self.assertEqual(item["source_fields"]["webaddr"], "college.example.edu/")
        self.assertEqual(item["source_fields"]["official_url_https_evidence"], row["ADMINURL"])

    def test_no_false_location_from_blank_nonfinite_or_invalid_coordinates(self):
        for lat, lon in (("", ""), ("nan", "-100"), ("30", "inf"), ("95", "-100"), ("0", "0")):
            self.assertIsNone(COLLEGES.record(fixture(LATITUDE=lat, LONGITUD=lon))["location"])

    def test_curated_crosswalk_requires_stable_unitid_and_exact_directory_name(self):
        item = COLLEGES.record(fixture(UNITID="166027", INSTNM="Harvard University"))
        self.assertEqual(item["curated_id"], "harvard")
        self.assertNotIn("curated_id", COLLEGES.record(fixture(INSTNM="Harvard University")))
        with self.assertRaisesRegex(ValueError, "requires review"):
            COLLEGES.record(fixture(UNITID="166027", INSTNM="Different Institution"))

    def test_aliases_do_not_split_internal_commas_or_infer_parent_relationships(self):
        item = COLLEGES.record(fixture(IALIAS="Example College, Main Campus|EC;EC", F1SYSNAM="Example System"))
        self.assertEqual(item["aliases"], ["Example College, Main Campus", "EC"])
        self.assertNotIn("parents", item)
        self.assertNotIn("leader", item)
        self.assertNotIn("governance", item)

    def test_csv_rejects_duplicate_ids_instead_of_silent_deduplication(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "hd2025.csv"
            with path.open("w", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=sorted(COLLEGES.REQUIRED))
                writer.writeheader()
                writer.writerows([fixture(), fixture()])
            with self.assertRaisesRegex(ValueError, "Duplicate UNITID"):
                COLLEGES.read_rows(path)

    def test_snapshot_is_reproducible_and_accounts_for_every_source_row(self):
        actual = COLLEGES.build_catalog(COLLEGES.SOURCE_DIR / "hd2025.csv")
        expected = json.loads(COLLEGES.OUTPUT.read_text())
        self.assertEqual(actual, expected)
        metadata = actual["metadata"]
        self.assertEqual(metadata["raw_count"], metadata["included_count"] + metadata["excluded_count"])
        self.assertEqual(metadata["excluded_count"], sum(metadata["counts"]["exclusions"].values()))
        self.assertEqual(metadata["included_count"], len(actual["records"]))
        self.assertEqual(metadata["counts"]["degree_granting"] + metadata["counts"]["nondegree_granting"], metadata["included_count"])


if __name__ == "__main__":
    unittest.main()
