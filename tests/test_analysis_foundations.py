import sqlite3
import tempfile
import unittest
from pathlib import Path

from database import db
from engine.reasoning_engine import ReasoningEngine
from pipeline.import_clinvar import normalize_clnsig
from pipeline.validate_knowledge_base import REQUIRED_TABLES, validate


class ClinVarNormalizationTests(unittest.TestCase):
    def test_pathogenic_label_wins_over_secondary_drug_response_label(self):
        self.assertEqual(
            normalize_clnsig("Pathogenic|drug_response"),
            "Pathogenic",
        )

    def test_conflicting_label_is_not_promoted_to_pathogenic(self):
        self.assertEqual(
            normalize_clnsig(
                "Pathogenic|Conflicting_interpretations_of_pathogenicity"
            ),
            "Conflicting_interpretations_of_pathogenicity",
        )

    def test_url_encoded_values_are_normalized(self):
        self.assertEqual(
            normalize_clnsig("Likely_pathogenic%7Cdrug_response"),
            "Likely_pathogenic",
        )


class GenotypeTests(unittest.TestCase):
    def test_homozygous_genotypes_are_not_classified_as_heterozygous(self):
        self.assertEqual(ReasoningEngine._genotype_to_zygosity("1/1"), "homozygous")
        self.assertEqual(ReasoningEngine._genotype_to_zygosity("1|1"), "homozygous")

    def test_gt_format_subfield_is_ignored_for_zygosity(self):
        self.assertEqual(
            ReasoningEngine._genotype_to_zygosity("0/1:42:99"),
            "heterozygous",
        )


class DatabaseInitializationTests(unittest.TestCase):
    def test_initialization_creates_the_full_v3_schema(self):
        with tempfile.TemporaryDirectory() as directory:
            original_path = db.DB_PATH
            try:
                db.DB_PATH = Path(directory) / "knowledge.db"
                db.init_db()
                result = validate(db.DB_PATH)
                self.assertFalse(result["missing_tables"])
                self.assertTrue(REQUIRED_TABLES.issubset(self._tables(db.DB_PATH)))
                self.assertFalse(result["ok"])  # Schema is ready; data is not loaded yet.
            finally:
                db.DB_PATH = original_path

    @staticmethod
    def _tables(db_path):
        with sqlite3.connect(db_path) as conn:
            return {
                row[0] for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            }


if __name__ == "__main__":
    unittest.main()
