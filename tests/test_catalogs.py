"""Catalog integration boundaries: provenance, identity, and unknown facts."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from catalogs import merge_catalogs
from build import valid_url


def directory_record(node_id="directory-example", **changes):
    value = {
        "id": node_id, "name": "Example Institution", "domain": "university",
        "category": "university_campus", "jurisdiction": "US", "record_kind": "directory",
        "catalog_source": "test-directory", "official_url": "https://example.edu/",
        "registry_url": "https://example.gov/institution/123456", "aliases": ["Example"],
        "identifiers": {"unitid": "123456"}, "location": None,
    }
    value.update(changes)
    return value


def known_location():
    return {"lat": 37.4, "lon": -122.1, "city": "Example City", "state": "CA", "precision": "campus", "evidence_url": "https://example.gov/institution/123456"}


class CatalogMergeTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.directory = self.root / "data" / "catalogs"
        self.directory.mkdir(parents=True)
        self.snapshot = self.root / "data" / "source.csv"
        self.snapshot.write_bytes(b"id,name\n123456,Example Institution\n")
        self.catalog = {
            "metadata": {
                "id": "test-directory", "title": "Official test directory",
                "source_url": "https://example.gov/directory.csv", "retrieved_at": "2026-10-24",
                "source_period": "2025-26", "raw_file": "data/source.csv",
                "sha256": hashlib.sha256(self.snapshot.read_bytes()).hexdigest(),
                "raw_count": 1, "included_count": 1, "excluded_count": 0,
            },
            "records": [directory_record()],
        }

    def merge(self, entities=None, catalog=None):
        value = self.catalog if catalog is None else catalog
        (self.directory / "test.json").write_text(json.dumps(value), encoding="utf-8")
        entities = {} if entities is None else entities
        metadata = merge_catalogs(self.directory, entities, self.root, valid_url)
        return entities, metadata

    def test_hash_rejects_tampered_snapshot(self):
        self.snapshot.write_bytes(b"changed upstream content")
        with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
            self.merge()

    def test_snapshot_cannot_escape_repository(self):
        self.catalog["metadata"]["raw_file"] = "../../outside.csv"
        with self.assertRaisesRegex(ValueError, "repository file"):
            self.merge()

    def test_missing_snapshot_provenance_is_rejected(self):
        del self.catalog["metadata"]["raw_file"]
        with self.assertRaisesRegex(ValueError, "provenance required"):
            self.merge()

    def test_multiple_raw_files_each_require_correct_hash(self):
        self.catalog["metadata"]["raw_files"] = [
            {"path": "data/source.csv", "sha256": self.catalog["metadata"]["sha256"]},
            {"path": "data/source.csv", "sha256": "0" * 64},
        ]
        with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
            self.merge()

    def test_crosswalk_fills_identity_and_missing_location_preserves_research(self):
        governance = {"apex": "Board of Trustees", "mechanism": "Recorded majority vote", "evidence_url": "https://example.edu/charter"}
        leader = {"name": "Reviewed Leader", "title": "President"}
        reviewed = {"id": "curated-example", "name": "Reviewed Institution", "official_url": "https://reviewed.example.edu/", "location": None, "governance": governance, "leader": leader, "identifiers": {"internal": "stable-7"}, "aliases": ["Reviewed"]}
        self.catalog["records"][0].update(curated_id="curated-example", location=known_location())
        result, meta = self.merge({"curated-example": copy.deepcopy(reviewed)})
        self.assertEqual(set(result), {"curated-example"})
        node = result["curated-example"]
        self.assertEqual(node["identifiers"], {"internal": "stable-7", "unitid": "123456"})
        self.assertEqual(node["location"], known_location())
        self.assertEqual(node["governance"], governance)
        self.assertEqual(node["leader"], leader)
        self.assertEqual(node["name"], "Reviewed Institution")
        self.assertEqual(node["official_url"], reviewed["official_url"])
        self.assertIn("directory-example", node["aliases"])
        self.assertEqual(node["catalog_records"][0]["record_id"], "directory-example")
        self.assertEqual(meta[0]["matched_curated_count"], 1)
        self.assertEqual(meta[0]["new_directory_count"], 0)

    def test_crosswalk_preserves_existing_reviewed_location(self):
        existing_location = {**known_location(), "lat": 40.1, "lon": -75.1, "state": "PA"}
        self.catalog["records"][0].update(curated_id="curated-example", location=known_location())
        result, _ = self.merge({"curated-example": {"id": "curated-example", "location": existing_location}})
        self.assertEqual(result["curated-example"]["location"], existing_location)

    def test_crosswalk_rejects_conflicting_existing_identifier(self):
        self.catalog["records"][0]["curated_id"] = "curated-example"
        original = {"id": "curated-example", "identifiers": {"unitid": "654321"}}
        with self.assertRaisesRegex(ValueError, "identifier"):
            self.merge({"curated-example": original})
        self.assertEqual(original["identifiers"]["unitid"], "654321")

    def test_directory_does_not_create_parents_leader_or_financial_facts(self):
        self.catalog["records"][0].update(parents=[{"parent_id": "made-up", "type": "PART_OF"}], leader={"name": "Historical Source Name"}, financial_profile=[{"value": 100}], employee_count=900, function="unreviewed")
        result, meta = self.merge()
        node = result["directory-example"]
        self.assertEqual(node["parents"], [])
        self.assertIsNone(node["leader"])
        self.assertIsNone(node["employee_count"])
        self.assertIsNone(node["function"])
        self.assertEqual(node["financial_profile"], [])
        self.assertEqual(node["verification_status"], "unverified")
        self.assertIsNone(node["verified_at"])
        self.assertEqual(meta[0]["new_directory_count"], 1)

    def test_unknown_location_and_website_remain_null(self):
        self.catalog["records"][0]["official_url"] = None
        result, _ = self.merge()
        self.assertIsNone(result["directory-example"]["location"])
        self.assertIsNone(result["directory-example"]["official_url"])
        self.assertEqual(result["directory-example"]["sources"][0]["url"], "https://example.gov/institution/123456")

    def test_duplicate_directory_id_is_rejected(self):
        self.catalog["records"].append(copy.deepcopy(self.catalog["records"][0]))
        self.catalog["metadata"]["included_count"] = 2
        with self.assertRaisesRegex(ValueError, "duplicate catalog id"):
            self.merge()

    def test_catalog_id_cannot_shadow_existing_researched_node(self):
        with self.assertRaisesRegex(ValueError, "duplicate catalog id"):
            self.merge({"directory-example": {"id": "directory-example"}})

    def test_duplicate_or_missing_curated_crosswalk_is_rejected(self):
        self.catalog["records"][0]["curated_id"] = "curated-example"
        with self.assertRaisesRegex(ValueError, "curated crosswalk"):
            self.merge()
        self.catalog["records"].append(directory_record("directory-other", curated_id="curated-example"))
        self.catalog["metadata"]["included_count"] = 2
        with self.assertRaisesRegex(ValueError, "curated crosswalk"):
            self.merge({"curated-example": {"id": "curated-example"}})

    def test_crosswalk_cannot_merge_two_directory_records_as_curated(self):
        self.catalog["records"][0]["curated_id"] = "another-directory"
        with self.assertRaisesRegex(ValueError, "curated crosswalk"):
            self.merge({"another-directory": {"id": "another-directory", "record_kind": "directory"}})

    def test_invalid_source_official_and_registry_urls_are_rejected(self):
        for location, field, value in (("metadata", "source_url", "http://example.gov/data"), ("record", "official_url", "javascript:alert(1)"), ("record", "registry_url", "https://user:secret@example.gov/private")):
            with self.subTest(field=field):
                changed = copy.deepcopy(self.catalog)
                target = changed["metadata"] if location == "metadata" else changed["records"][0]
                target[field] = value
                with self.assertRaisesRegex(ValueError, "URL|url"):
                    self.merge(catalog=changed)

    def test_invalid_coordinates_and_location_evidence_are_rejected(self):
        for updates in ({"lat": 95}, {"lon": float("nan")}, {"lat": True}, {"evidence_url": "http://example.gov/location"}):
            with self.subTest(updates=updates):
                changed = copy.deepcopy(self.catalog)
                changed["records"][0]["location"] = {**known_location(), **updates}
                with self.assertRaisesRegex(ValueError, "invalid location"):
                    self.merge(catalog=changed)

    def test_location_requires_complete_shape_or_null(self):
        for location in ({}, [], {**known_location(), "precision": "unknown"}, {key: value for key, value in known_location().items() if key != "city"}, {**known_location(), "state": ""}):
            with self.subTest(location=location):
                changed = copy.deepcopy(self.catalog)
                changed["records"][0]["location"] = location
                with self.assertRaisesRegex(ValueError, "location"):
                    self.merge(catalog=changed)

    def test_included_count_mismatch_is_rejected(self):
        self.catalog["metadata"]["included_count"] = 2
        with self.assertRaisesRegex(ValueError, "included_count mismatch"):
            self.merge()

    def test_raw_count_requires_nonnegative_integer(self):
        for value in (-1, True, "1", 1.2):
            with self.subTest(raw_count=value):
                changed = copy.deepcopy(self.catalog)
                changed["metadata"]["raw_count"] = value
                with self.assertRaisesRegex(ValueError, "count"):
                    self.merge(catalog=changed)

    def test_catalog_source_must_match_its_metadata(self):
        self.catalog["records"][0]["catalog_source"] = "different-source"
        with self.assertRaisesRegex(ValueError, "inconsistent catalog source"):
            self.merge()


if __name__ == "__main__":
    unittest.main()
