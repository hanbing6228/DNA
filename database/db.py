#!/usr/bin/env python3
import sqlite3
import json
from pathlib import Path
from contextlib import contextmanager
from typing import Optional, List, Dict

DB_PATH = Path(__file__).parent / "dna_knowledge.db"
SCHEMA_PATH = Path(__file__).parent / "schema.sql"
V3_SCHEMA_PATH = Path(__file__).parent / "schema_v3.sql"

def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    try:
        # Both schemas are idempotent.  Keeping the v3 tables here prevents
        # callers other than the Flask app (for example the ClinVar importer)
        # from creating an incomplete database.
        conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        conn.executescript(V3_SCHEMA_PATH.read_text(encoding="utf-8"))
        conn.commit()
    finally:
        conn.close()
    print("Database initialized:", DB_PATH)

@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

class GeneRepository:
    @staticmethod
    def upsert(symbol: str, **kwargs) -> int:
        with get_conn() as conn:
            cur = conn.execute("SELECT id FROM genes WHERE symbol = ?", (symbol,))
            row = cur.fetchone()
            if row:
                gid = row["id"]
                if kwargs:
                    fields = ", ".join(f"{k}=?" for k in kwargs)
                    conn.execute(f"UPDATE genes SET {fields} WHERE id=?", (*kwargs.values(), gid))
                    conn.commit()
                return gid
            cols = ["symbol"] + list(kwargs.keys())
            vals = [symbol] + list(kwargs.values())
            ph = ", ".join(["?"] * len(cols))
            conn.execute(f"INSERT INTO genes ({', '.join(cols)}) VALUES ({ph})", vals)
            conn.commit()
            return conn.execute("SELECT last_insert_rowid()").fetchone()[0]

    @staticmethod
    def get_by_symbol(symbol: str) -> Optional[Dict]:
        with get_conn() as conn:
            row = conn.execute("SELECT * FROM genes WHERE symbol = ?", (symbol,)).fetchone()
            return dict(row) if row else None

class DiseaseRepository:
    @staticmethod
    def upsert(name: str, **kwargs) -> int:
        with get_conn() as conn:
            cur = conn.execute("SELECT id FROM diseases WHERE name = ?", (name,))
            row = cur.fetchone()
            if row:
                return row["id"]
            cols = ["name"] + list(kwargs.keys())
            vals = [name] + list(kwargs.values())
            ph = ", ".join(["?"] * len(cols))
            conn.execute(f"INSERT INTO diseases ({', '.join(cols)}) VALUES ({ph})", vals)
            conn.commit()
            return conn.execute("SELECT last_insert_rowid()").fetchone()[0]

    @staticmethod
    def get_by_name(name: str) -> Optional[Dict]:
        with get_conn() as conn:
            row = conn.execute("SELECT * FROM diseases WHERE name = ?", (name,)).fetchone()
            return dict(row) if row else None

class VariantRepository:
    @staticmethod
    def upsert(chrom: str, pos: int, ref: str, alt: str, **kwargs) -> int:
        with get_conn() as conn:
            cur = conn.execute(
                "SELECT id FROM variants WHERE chromosome=? AND position=? AND reference=? AND alternate=?",
                (chrom, pos, ref, alt)
            )
            row = cur.fetchone()
            if row:
                vid = row["id"]
                if kwargs:
                    fields = ", ".join(f"{k}=?" for k in kwargs)
                    conn.execute(f"UPDATE variants SET {fields} WHERE id=?", (*kwargs.values(), vid))
                    conn.commit()
                return vid
            cols = ["chromosome", "position", "reference", "alternate"] + list(kwargs.keys())
            vals = [chrom, pos, ref, alt] + list(kwargs.values())
            ph = ", ".join(["?"] * len(cols))
            conn.execute(f"INSERT INTO variants ({', '.join(cols)}) VALUES ({ph})", vals)
            conn.commit()
            return conn.execute("SELECT last_insert_rowid()").fetchone()[0]

    @staticmethod
    def find_by_location(chrom: str, pos: int, ref: str, alt: str) -> Optional[Dict]:
        with get_conn() as conn:
            row = conn.execute(
                "SELECT v.*, g.symbol as gene_symbol FROM variants v LEFT JOIN genes g ON v.gene_id = g.id "
                "WHERE v.chromosome=? AND v.position=? AND v.reference=? AND v.alternate=?",
                (chrom, pos, ref, alt)
            ).fetchone()
            return dict(row) if row else None

    @staticmethod
    def find_pathogenic_by_gene(gene_symbol: str) -> List[Dict]:
        with get_conn() as conn:
            rows = conn.execute(
                "SELECT v.* FROM variants v JOIN genes g ON v.gene_id = g.id "
                "WHERE g.symbol = ? AND v.clinvar_significance IN "
                "('Pathogenic', 'Likely_pathogenic', 'Pathogenic/Likely_pathogenic')",
                (gene_symbol,)
            ).fetchall()
            return [dict(r) for r in rows]

class VariantDiseaseRepository:
    @staticmethod
    def link(variant_id: int, disease_id: int, **kwargs):
        with get_conn() as conn:
            cols = ["variant_id", "disease_id"] + list(kwargs.keys())
            vals = [variant_id, disease_id] + list(kwargs.values())
            ph = ", ".join(["?"] * len(cols))
            conn.execute(f"INSERT OR REPLACE INTO variant_disease ({', '.join(cols)}) VALUES ({ph})", vals)
            conn.commit()

class MedicationRepository:
    @staticmethod
    def upsert(drug_name: str, **kwargs) -> int:
        with get_conn() as conn:
            cur = conn.execute("SELECT id FROM medications WHERE drug_name = ?", (drug_name,))
            row = cur.fetchone()
            if row:
                return row["id"]
            cols = ["drug_name"] + list(kwargs.keys())
            vals = [drug_name] + list(kwargs.values())
            ph = ", ".join(["?"] * len(cols))
            conn.execute(f"INSERT INTO medications ({', '.join(cols)}) VALUES ({ph})", vals)
            conn.commit()
            return conn.execute("SELECT last_insert_rowid()").fetchone()[0]

    @staticmethod
    def get_guidance_for_variant(variant_id: int) -> List[Dict]:
        with get_conn() as conn:
            rows = conn.execute(
                "SELECT m.drug_name, m.drug_class, vm.effect, vm.recommendation, vm.guideline_source "
                "FROM variant_medication vm JOIN medications m ON vm.medication_id = m.id "
                "WHERE vm.variant_id = ?", (variant_id,)
            ).fetchall()
            return [dict(r) for r in rows]

class UserGenotypeRepository:
    @staticmethod
    def save(sample: str, variant_id: int, genotype: str, quality: float = None):
        zyg = "heterozygous" if genotype in ("0/1", "0|1", "1/0", "1|0") else               "homozygous" if genotype in ("1/1", "1|1") else               "hemizygous" if genotype in ("1", "0") else "unknown"
        with get_conn() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO user_genotypes (sample_name, variant_id, genotype, zygosity, quality) VALUES (?, ?, ?, ?, ?)",
                (sample, variant_id, genotype, zyg, quality)
            )
            conn.commit()

    @staticmethod
    def get_findings(sample: str) -> List[Dict]:
        with get_conn() as conn:
            rows = conn.execute(
                "SELECT v.*, g.symbol as gene_symbol, ug.genotype, ug.zygosity FROM user_genotypes ug "
                "JOIN variants v ON ug.variant_id = v.id LEFT JOIN genes g ON v.gene_id = g.id "
                "WHERE ug.sample_name = ? AND v.clinvar_significance IN "
                "('Pathogenic', 'Likely_pathogenic', 'Pathogenic/Likely_pathogenic', 'drug_response')",
                (sample,)
            ).fetchall()
            return [dict(r) for r in rows]


class KnowledgeSourceRepository:
    @staticmethod
    def upsert(source_key: str, display_name: str, category: str, **kwargs) -> int:
        with get_conn() as conn:
            row = conn.execute(
                "SELECT id FROM knowledge_sources WHERE source_key = ?",
                (source_key,),
            ).fetchone()
            if row:
                if kwargs:
                    fields = ", ".join(f"{field}=?" for field in kwargs)
                    conn.execute(
                        f"UPDATE knowledge_sources SET display_name=?, category=?, {fields} WHERE id=?",
                        (display_name, category, *kwargs.values(), row["id"]),
                    )
                    conn.commit()
                return row["id"]
            columns = ["source_key", "display_name", "category", *kwargs.keys()]
            values = [source_key, display_name, category, *kwargs.values()]
            placeholders = ", ".join("?" for _ in columns)
            conn.execute(
                f"INSERT INTO knowledge_sources ({', '.join(columns)}) VALUES ({placeholders})",
                values,
            )
            conn.commit()
            return conn.execute("SELECT last_insert_rowid()").fetchone()[0]


class GenomicContextRepository:
    @staticmethod
    def add_gene_function(gene_id: int, source_id: int, term_name: str, **kwargs) -> None:
        columns = ["gene_id", "source_id", "term_name", *kwargs.keys()]
        values = [gene_id, source_id, term_name, *kwargs.values()]
        placeholders = ", ".join("?" for _ in columns)
        with get_conn() as conn:
            conn.execute(
                f"INSERT OR REPLACE INTO gene_functions ({', '.join(columns)}) VALUES ({placeholders})",
                values,
            )
            conn.commit()

    @staticmethod
    def get_gene_functions(symbol: str) -> List[Dict]:
        with get_conn() as conn:
            rows = conn.execute(
                "SELECT gf.aspect, gf.term_id, gf.term_name, gf.evidence_code, gf.description, "
                "ks.display_name AS source, ks.version_tag, ks.source_url "
                "FROM gene_functions gf "
                "JOIN genes g ON g.id = gf.gene_id "
                "JOIN knowledge_sources ks ON ks.id = gf.source_id "
                "WHERE g.symbol = ? ORDER BY gf.term_name",
                (symbol,),
            ).fetchall()
            return [dict(row) for row in rows]

    @staticmethod
    def add_trait_association(record: Dict) -> None:
        columns = list(record.keys())
        placeholders = ", ".join("?" for _ in columns)
        with get_conn() as conn:
            conn.execute(
                f"INSERT OR REPLACE INTO variant_traits ({', '.join(columns)}) VALUES ({placeholders})",
                [record[column] for column in columns],
            )
            conn.commit()

    @staticmethod
    def add_ancestry_marker(record: Dict) -> None:
        columns = list(record.keys())
        placeholders = ", ".join("?" for _ in columns)
        with get_conn() as conn:
            conn.execute(
                f"INSERT OR REPLACE INTO ancestry_markers ({', '.join(columns)}) VALUES ({placeholders})",
                [record[column] for column in columns],
            )
            conn.commit()

    @staticmethod
    def get_ancestry_markers() -> List[Dict]:
        with get_conn() as conn:
            rows = conn.execute(
                "SELECT chromosome, position, reference, alternate, population_code, "
                "alternate_allele_frequency FROM ancestry_markers"
            ).fetchall()
            return [dict(row) for row in rows]


class ExternalQueryCacheRepository:
    @staticmethod
    def get(source_id: int, query_key: str) -> Optional[Dict]:
        with get_conn() as conn:
            row = conn.execute(
                "SELECT payload_json, fetched_at, expires_at FROM external_query_cache "
                "WHERE source_id = ? AND query_key = ? "
                "AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP)",
                (source_id, query_key),
            ).fetchone()
            if not row:
                return None
            return {
                "payload": json.loads(row["payload_json"]),
                "fetched_at": row["fetched_at"],
                "expires_at": row["expires_at"],
                "cached": True,
            }

    @staticmethod
    def save(source_id: int, query_key: str, payload: Dict, expires_at: str) -> None:
        with get_conn() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO external_query_cache "
                "(source_id, query_key, payload_json, expires_at) VALUES (?, ?, ?, ?)",
                (source_id, query_key, json.dumps(payload, ensure_ascii=False), expires_at),
            )
            conn.commit()
