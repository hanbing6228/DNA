import sqlite3
import tempfile
import unittest
import json
from pathlib import Path
from types import SimpleNamespace

from database import db
from database.db import (
    GeneRepository,
    GenomicContextRepository,
    KnowledgeSourceRepository,
)
from engine.genomic_context import AncestryService, GeneFunctionService
from engine.external_sources import EnsemblClient, GWASCatalogClient, JsonHttpClient
from engine.reasoning_engine import ReasoningEngine
from pipeline.import_clinvar import normalize_clnsig
from pipeline.import_genomic_context import import_functions
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


class GenomicContextTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.original_path = db.DB_PATH
        db.DB_PATH = Path(self.directory.name) / "knowledge.db"
        db.init_db()

    def tearDown(self):
        db.DB_PATH = self.original_path
        self.directory.cleanup()

    def test_gene_functions_remain_attributed_to_their_source(self):
        source_id = KnowledgeSourceRepository.upsert(
            "go-2026-01", "Gene Ontology", "gene_function",
            version_tag="2026-01", source_url="https://geneontology.org", license="CC BY 4.0",
        )
        gene_id = GeneRepository.upsert("BRCA1")
        GenomicContextRepository.add_gene_function(
            gene_id, source_id, "DNA repair", term_id="GO:0006281", aspect="biological_process",
        )
        function = GeneFunctionService.get_summary("BRCA1")[0]
        self.assertEqual(function["term_id"], "GO:0006281")
        self.assertEqual(function["source"], "Gene Ontology")

    def test_ancestry_estimate_is_marked_exploratory_for_small_panel(self):
        source_id = KnowledgeSourceRepository.upsert("panel-v1", "Test panel", "ancestry_reference")
        for population, frequency in (("POP_A", 0.8), ("POP_B", 0.2)):
            GenomicContextRepository.add_ancestry_marker({
                "chromosome": "1", "position": 100, "reference": "A", "alternate": "G",
                "population_code": population, "alternate_allele_frequency": frequency,
                "source_id": source_id,
            })
        result = AncestryService.analyze([
            {"chrom": "1", "pos": 100, "ref": "A", "alt": "G", "genotype": "1/1"}
        ])
        self.assertEqual(result["status"], "exploratory")
        self.assertEqual(result["matched_loci"], 1)
        self.assertEqual(result["results"][0]["reference_population"], "POP_A")

    def test_function_import_requires_and_preserves_source_metadata(self):
        input_path = Path(self.directory.name) / "functions.tsv"
        input_path.write_text(
            "gene_symbol\tterm_id\tterm_name\taspect\tevidence_code\tdescription\n"
            "CFTR\tGO:0006820\tanion transport\tbiological_process\tIDA\tExample annotation\n",
            encoding="utf-8",
        )
        args = SimpleNamespace(
            input=input_path,
            delimiter="\t",
            source_key="go-test-v1",
            source_name="Gene Ontology",
            version="test-v1",
            source_url="https://geneontology.org",
            license="CC BY 4.0",
        )
        self.assertEqual(import_functions(args), 1)
        function = GeneFunctionService.get_summary("CFTR")[0]
        self.assertEqual(function["term_name"], "anion transport")
        self.assertEqual(function["version_tag"], "test-v1")


class ExternalSourceTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.original_path = db.DB_PATH
        db.DB_PATH = Path(self.directory.name) / "knowledge.db"
        db.init_db()
        self.calls = []

    def tearDown(self):
        db.DB_PATH = self.original_path
        self.directory.cleanup()

    def _opener(self, request, timeout):
        self.calls.append(request.full_url)
        if "lookup/symbol" in request.full_url:
            return _JsonResponse({"id": "ENSG00000012048"})
        if "xrefs/id" in request.full_url:
            return _JsonResponse([
                {"dbname": "GO", "primary_id": "GO:0006281", "description": "DNA repair"},
                {"dbname": "HGNC", "primary_id": "1100", "description": "BRCA1"},
            ])
        return _JsonResponse({"_embedded": {"associations": [{"p_value": 1e-9, "trait": "test trait"}]}})

    def test_ensembl_function_response_is_cached_with_go_terms(self):
        client = EnsemblClient(JsonHttpClient(opener=self._opener))
        first = client.gene_functions("brca1")
        second = client.gene_functions("brca1")
        self.assertFalse(first["cached"])
        self.assertTrue(second["cached"])
        self.assertEqual(first["payload"]["functions"][0]["term_id"], "GO:0006281")
        self.assertEqual(len(self.calls), 2)

    def test_gwas_association_response_is_cached_by_rsid(self):
        client = GWASCatalogClient(JsonHttpClient(opener=self._opener))
        result = client.associations("rs429358")
        self.assertEqual(result["payload"]["rsid"], "rs429358")
        self.assertEqual(result["payload"]["associations"][0]["trait"], "test trait")
        self.assertEqual(client.associations("rs429358")["cached"], True)


class _JsonResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


if __name__ == "__main__":
    unittest.main()
