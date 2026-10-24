import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from catalog_identity import merge_catalog_identities
from build import valid_url


class CatalogIdentityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.real_document = json.loads((ROOT / "data/catalog-links.json").read_text())
        link = cls.real_document["links"][0]
        cls.real_nodes = {}
        for catalog, node_id in (("agencies", link["source_id"]), ("ipeds", link["target_id"])):
            records = json.loads((ROOT / "data/catalogs" / (catalog + ".json")).read_text())["records"]
            node = copy.deepcopy(next(r for r in records if r["id"] == node_id))
            node.update(parents=[], leader=None, catalog_records=[{"source_id": catalog, "record_id": node_id}], sources=[{"url": node["registry_url"], "description": catalog}])
            cls.real_nodes[node_id] = node

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "data").mkdir()
        self.document = copy.deepcopy(self.real_document)
        self.link = self.document["links"][0]
        self.entities = copy.deepcopy(self.real_nodes)

    def merge(self):
        (self.root / "data/catalog-links.json").write_text(json.dumps(self.document))
        return merge_catalog_identities(self.entities, self.root, valid_url)

    def test_explicit_link_reduces_count_preserves_primary_identity_and_both_provenances(self):
        primary = copy.deepcopy(self.entities[self.link["target_id"]])
        links = self.merge()
        self.assertEqual(len(self.entities), 1)
        self.assertEqual(links, [self.link])
        node = self.entities[self.link["target_id"]]
        self.assertEqual(node["identifiers"], {"unitid": "197036", "usagov_node_id": "1066"})
        self.assertEqual(node["source_fields"], primary["source_fields"])
        self.assertEqual(node["location"], primary["location"])
        self.assertEqual(node["category"], "university_campus")
        self.assertEqual(node["catalog_source"], "ipeds")
        self.assertIn(self.link["source_id"], node["aliases"])
        self.assertEqual({p["source_id"] for p in node["catalog_records"]}, {"agencies", "ipeds"})
        self.assertIn("usagov", node["identity_sources"][0]["source_fields"])
        self.assertEqual(len(node["sources"]), 2)
        self.assertEqual(node["parents"], [])
        self.assertIsNone(node["leader"])

    def test_no_link_file_means_no_automatic_website_matching(self):
        self.assertEqual(merge_catalog_identities(self.entities, self.root, valid_url), [])
        self.assertEqual(len(self.entities), 2)

    def test_conflicting_identifiers_reject_without_partial_mutation(self):
        self.entities[self.link["source_id"]]["identifiers"]["unitid"] = "wrong-campus"
        before = copy.deepcopy(self.entities)
        with self.assertRaisesRegex(ValueError, "identifier conflict"):
            self.merge()
        self.assertEqual(before, self.entities)

    def test_missing_target_rejected(self):
        del self.entities[self.link["target_id"]]
        with self.assertRaisesRegex(ValueError, "missing"):
            self.merge()

    def test_malformed_or_unmatched_evidence_url_rejected(self):
        for field, value in (("source_registry_url", "javascript:alert(1)"), ("target_registry_url", "https://example.gov/wrong"), ("official_url", "http://www.westpoint.edu/")):
            with self.subTest(field=field):
                original = self.link[field]
                self.link[field] = value
                with self.assertRaises(ValueError):
                    self.merge()
                self.link[field] = original

    def test_curated_or_structurally_connected_source_cannot_be_removed(self):
        source = self.entities[self.link["source_id"]]
        source["record_kind"] = "curated"
        with self.assertRaisesRegex(ValueError, "curated"):
            self.merge()
        source["record_kind"] = "directory"
        self.entities["child"] = {"parents": [{"parent_id": source["id"]}]}
        with self.assertRaisesRegex(ValueError, "structural edges"):
            self.merge()

    def test_changed_reviewed_name_requires_reverification(self):
        self.entities[self.link["target_id"]]["name"] = "Another Academy"
        with self.assertRaisesRegex(ValueError, "names changed"):
            self.merge()


if __name__ == "__main__":
    unittest.main()
