#!/usr/bin/env python3
import sqlite3
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
