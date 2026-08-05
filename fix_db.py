import sqlite3
from pathlib import Path

# 1. Delete old broken db
p = Path('database/dna_knowledge.db')
if p.exists():
    p.unlink()
    print('Deleted old db')

# 2. Write clean schema.sql
schema = """CREATE TABLE IF NOT EXISTS genes (
id INTEGER PRIMARY KEY AUTOINCREMENT,
symbol TEXT UNIQUE NOT NULL,
ensembl_id TEXT,
name TEXT,
chromosome TEXT,
description TEXT,
inheritance_pattern TEXT
);
CREATE TABLE IF NOT EXISTS diseases (
id INTEGER PRIMARY KEY AUTOINCREMENT,
name TEXT UNIQUE NOT NULL,
omim_id TEXT,
mondo_id TEXT,
icd10 TEXT,
description TEXT,
severity TEXT,
age_of_onset TEXT,
inheritance TEXT
);
CREATE TABLE IF NOT EXISTS variants (
id INTEGER PRIMARY KEY AUTOINCREMENT,
chromosome TEXT NOT NULL,
position INTEGER NOT NULL,
reference TEXT NOT NULL,
alternate TEXT NOT NULL,
gene_id INTEGER,
hgvs_genomic TEXT,
hgvs_coding TEXT,
hgvs_protein TEXT,
clinvar_significance TEXT,
clinvar_review_status TEXT,
dbsnp_id TEXT,
clinvar_variation_id TEXT,
raw_info TEXT,
source TEXT DEFAULT 'clinvar',
imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
FOREIGN KEY (gene_id) REFERENCES genes(id)
);
CREATE TABLE IF NOT EXISTS variant_disease (
variant_id INTEGER NOT NULL,
disease_id INTEGER NOT NULL,
significance TEXT,
evidence_level TEXT,
penetrance REAL,
mechanism TEXT,
PRIMARY KEY (variant_id, disease_id),
FOREIGN KEY (variant_id) REFERENCES variants(id),
FOREIGN KEY (disease_id) REFERENCES diseases(id)
);
CREATE TABLE IF NOT EXISTS phenotypes (
id INTEGER PRIMARY KEY AUTOINCREMENT,
hpo_id TEXT UNIQUE,
name TEXT NOT NULL,
category TEXT
);
CREATE TABLE IF NOT EXISTS disease_phenotype (
disease_id INTEGER NOT NULL,
phenotype_id INTEGER NOT NULL,
frequency TEXT,
evidence TEXT,
PRIMARY KEY (disease_id, phenotype_id),
FOREIGN KEY (disease_id) REFERENCES diseases(id),
FOREIGN KEY (phenotype_id) REFERENCES phenotypes(id)
);
CREATE TABLE IF NOT EXISTS medications (
id INTEGER PRIMARY KEY AUTOINCREMENT,
drug_name TEXT NOT NULL,
drug_class TEXT,
rxnorm_id TEXT,
description TEXT
);
CREATE TABLE IF NOT EXISTS variant_medication (
variant_id INTEGER NOT NULL,
medication_id INTEGER NOT NULL,
effect TEXT,
recommendation TEXT,
guideline_source TEXT,
PRIMARY KEY (variant_id, medication_id),
FOREIGN KEY (variant_id) REFERENCES variants(id),
FOREIGN KEY (medication_id) REFERENCES medications(id)
);
CREATE TABLE IF NOT EXISTS user_genotypes (
id INTEGER PRIMARY KEY AUTOINCREMENT,
sample_name TEXT,
variant_id INTEGER NOT NULL,
genotype TEXT,
zygosity TEXT,
quality REAL,
imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
FOREIGN KEY (variant_id) REFERENCES variants(id)
);"""

Path('database/schema.sql').write_text(schema, encoding='utf-8')
print('Wrote schema.sql')

# 3. Write clean db.py
db_code = """#!/usr/bin/env python3
import sqlite3
from pathlib import Path
from contextlib import contextmanager
from typing import Optional, List, Dict

DB_PATH = Path(__file__).parent / "dna_knowledge.db"
SCHEMA_PATH = Path(__file__).parent / "schema.sql"

def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    schema = SCHEMA_PATH.read_text(encoding="utf-8")
    for stmt in schema.split(";"):
        stmt = stmt.strip()
        if stmt:
            try:
                conn.execute(stmt)
            except sqlite3.OperationalError as e:
                if "already exists" not in str(e):
                    print("Warning:", e)
    conn.commit()
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
                "WHERE g.symbol = ? AND v.clinvar_significance IN ('Pathogenic', 'Likely_pathogenic')",
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
        zyg = "heterozygous" if genotype in ("0/1", "0|1", "1/0", "1|0") else \
              "homozygous" if genotype in ("1/1", "1|1") else \
              "hemizygous" if genotype in ("1", "0") else "unknown"
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
                "WHERE ug.sample_name = ? AND v.clinvar_significance IN ('Pathogenic', 'Likely_pathogenic', 'drug_response')",
                (sample,)
            ).fetchall()
            return [dict(r) for r in rows]
"""

Path('database/db.py').write_text(db_code, encoding='utf-8')
print('Wrote db.py')

# 4. Initialize
from database.db import init_db
init_db()
print('Done.')
