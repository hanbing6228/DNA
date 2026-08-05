#!/usr/bin/env python3
"""DNA v2.0 Installer - creates all architecture files in one run."""
import os
from pathlib import Path

BASE = Path(__file__).parent

FILES = {
    'database/__init__.py': '',

    'database/schema.sql': r"""-- DNA Knowledge Graph v2.0 Schema (SQLite)

CREATE TABLE IF NOT EXISTS genes (
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

CREATE INDEX idx_variants_loc ON variants(chromosome, position);
CREATE INDEX idx_variants_gene ON variants(gene_id);
CREATE INDEX idx_variants_significance ON variants(clinvar_significance);

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
);

CREATE INDEX idx_user_genotypes_sample ON user_genotypes(sample_name);
""",

    'database/db.py': r"""#!/usr/bin/env python3
import sqlite3
import json
from pathlib import Path
from contextlib import contextmanager
from typing import Optional, List, Dict

DB_PATH = Path(__file__).parent / "dna_knowledge.db"
SCHEMA_PATH = Path(__file__).parent / "schema.sql"


def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA_PATH.read_text(encoding='utf-8'))
    conn.commit()
    conn.close()
    print(f"Database initialized: {DB_PATH}")


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
                gene_id = row["id"]
                if kwargs:
                    fields = ", ".join(f"{k}=?" for k in kwargs)
                    conn.execute(f"UPDATE genes SET {fields} WHERE id=?", (*kwargs.values(), gene_id))
                    conn.commit()
                return gene_id
            cols = ["symbol"] + list(kwargs.keys())
            vals = [symbol] + list(kwargs.values())
            placeholders = ", ".join(["?"] * len(cols))
            conn.execute(f"INSERT INTO genes ({', '.join(cols)}) VALUES ({placeholders})", vals)
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
            placeholders = ", ".join(["?"] * len(cols))
            conn.execute(f"INSERT INTO diseases ({', '.join(cols)}) VALUES ({placeholders})", vals)
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
            placeholders = ", ".join(["?"] * len(cols))
            conn.execute(f"INSERT INTO variants ({', '.join(cols)}) VALUES ({placeholders})", vals)
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
            placeholders = ", ".join(["?"] * len(cols))
            conn.execute(f"INSERT OR REPLACE INTO variant_disease ({', '.join(cols)}) VALUES ({placeholders})", vals)
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
            placeholders = ", ".join(["?"] * len(cols))
            conn.execute(f"INSERT INTO medications ({', '.join(cols)}) VALUES ({placeholders})", vals)
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
""",

    'engine/__init__.py': '',

    'engine/knowledge_service.py': r"""#!/usr/bin/env python3
import sys
from pathlib import Path
from typing import List, Dict, Optional

sys.path.insert(0, str(Path(__file__).parent.parent))
from database.db import (
    GeneRepository, VariantRepository, DiseaseRepository,
    MedicationRepository, UserGenotypeRepository
)


class KnowledgeService:
    @staticmethod
    def get_variant(chrom: str, pos: int, ref: str, alt: str) -> Optional[Dict]:
        return VariantRepository.find_by_location(chrom, pos, ref, alt)

    @staticmethod
    def get_variant_by_gene_symbol(symbol: str) -> List[Dict]:
        return VariantRepository.find_pathogenic_by_gene(symbol)

    @staticmethod
    def get_gene(symbol: str) -> Optional[Dict]:
        return GeneRepository.get_by_symbol(symbol)

    @staticmethod
    def get_disease(name: str) -> Optional[Dict]:
        return DiseaseRepository.get_by_name(name)

    @staticmethod
    def get_drug_guidance_for_variant(variant_id: int) -> List[Dict]:
        return MedicationRepository.get_guidance_for_variant(variant_id)

    @staticmethod
    def get_user_findings(sample_name: str) -> List[Dict]:
        return UserGenotypeRepository.get_findings(sample_name)

    @staticmethod
    def search_variants_by_significance(significance: List[str]) -> List[Dict]:
        from database.db import get_conn
        with get_conn() as conn:
            placeholders = ','.join('?' * len(significance))
            rows = conn.execute(
                f"SELECT v.*, g.symbol as gene_symbol FROM variants v LEFT JOIN genes g ON v.gene_id = g.id "
                f"WHERE v.clinvar_significance IN ({placeholders})", significance
            ).fetchall()
            return [dict(r) for r in rows]
""",

    'engine/reasoning_engine.py': r"""#!/usr/bin/env python3
import sys
from pathlib import Path
from typing import Dict, List, Optional

sys.path.insert(0, str(Path(__file__).parent.parent))


class InheritanceRule:
    PATTERNS = {
        'AD': {'name': 'Autosomal Dominant', 'affected_heterozygous': True, 'affected_homozygous': True},
        'AR': {'name': 'Autosomal Recessive', 'affected_heterozygous': False, 'affected_homozygous': True},
        'XL': {'name': 'X-linked', 'affected_hemizygous': True, 'affected_heterozygous': False},
    }

    @classmethod
    def assess(cls, inheritance: str, zygosity: str, significance: str) -> Dict:
        result = {
            'pattern': inheritance or 'Unknown',
            'pattern_name': cls.PATTERNS.get(inheritance, {}).get('name', 'Unknown'),
            'zygosity': zygosity or 'unknown',
            'affected_status': False,
            'carrier_status': False,
            'penetrance': 1.0,
            'confidence': 'low',
            'explanation': ''
        }

        if significance not in ('Pathogenic', 'Likely_pathogenic', 'Pathogenic/Likely_pathogenic'):
            result['explanation'] = 'Variant not classified as pathogenic.'
            return result

        if inheritance == 'AD':
            if zygosity in ('heterozygous', 'homozygous'):
                result['affected_status'] = True
                result['penetrance'] = 0.8
                result['confidence'] = 'medium'
                result['explanation'] = 'Autosomal dominant: one pathogenic allele is sufficient to cause disease. Penetrance ~80%.'
        elif inheritance == 'AR':
            if zygosity == 'homozygous':
                result['affected_status'] = True
                result['confidence'] = 'high'
                result['explanation'] = 'Autosomal recessive: homozygous pathogenic variant - disease likely present.'
            elif zygosity == 'heterozygous':
                result['carrier_status'] = True
                result['confidence'] = 'high'
                result['explanation'] = 'Autosomal recessive: heterozygous carrier - typically asymptomatic.'
        elif inheritance == 'XL':
            if zygosity == 'hemizygous':
                result['affected_status'] = True
                result['confidence'] = 'high'
                result['explanation'] = 'X-linked: hemizygous male - disease likely present.'
            elif zygosity == 'heterozygous':
                result['carrier_status'] = True
                result['confidence'] = 'medium'
                result['explanation'] = 'X-linked: female carrier - may have mild symptoms or be asymptomatic.'
        else:
            if zygosity in ('heterozygous', 'homozygous', 'hemizygous'):
                result['affected_status'] = True
                result['confidence'] = 'low'
                result['explanation'] = 'Inheritance pattern unknown - cannot determine risk from zygosity alone.'

        return result


class EvidenceScorer:
    REVIEW_WEIGHTS = {
        'practice guideline': 4,
        'reviewed by expert panel': 3,
        'criteria provided multiple submitters no conflicts': 2,
        'criteria provided single submitter': 1,
        'criteria provided conflicting interpretations': 0,
        'no assertion criteria provided': -1,
        'no assertion provided': -2,
    }

    SIGNIFICANCE_SCORES = {
        'Pathogenic': 10,
        'Likely_pathogenic': 7,
        'Pathogenic/Likely_pathogenic': 8,
        'Uncertain_significance': 2,
        'Likely_benign': -2,
        'Benign': -5,
        'drug_response': 5,
    }

    @classmethod
    def score(cls, variant: Dict, inheritance_result: Dict) -> Dict:
        sig = variant.get('clinvar_significance', '')
        revstat = variant.get('clinvar_review_status', '') or ''

        sig_score = cls.SIGNIFICANCE_SCORES.get(sig, 0)
        rev_score = 0
        for key, weight in cls.REVIEW_WEIGHTS.items():
            if key in revstat.lower():
                rev_score = weight
                break

        inh = inheritance_result
        inh_bonus = 0
        if inh['affected_status'] and inh['confidence'] == 'high':
            inh_bonus = 3
        elif inh['carrier_status']:
            inh_bonus = 1

        total = sig_score + rev_score + inh_bonus

        return {
            'total_score': max(0, total),
            'significance_score': sig_score,
            'review_score': rev_score,
            'inheritance_bonus': inh_bonus,
            'priority': 'high' if total >= 10 else 'medium' if total >= 5 else 'low',
            'factors': {
                'clinvar_significance': sig,
                'review_status': revstat,
                'inheritance_pattern': inh['pattern'],
                'affected_status': inh['affected_status'],
                'carrier_status': inh['carrier_status'],
            }
        }


class RiskClassifier:
    @classmethod
    def classify(cls, variant: Dict, score: Dict, inheritance: Dict) -> Dict:
        sig = variant.get('clinvar_significance', '')

        if sig == 'drug_response':
            return {
                'category': 'pharmacogenomics',
                'category_cn': '药物基因组学',
                'icon': '💊',
                'urgency': 'medium',
                'description': '该变异可能影响药物代谢或反应，用药前建议咨询医生。'
            }

        if inheritance.get('affected_status') and score['total_score'] >= 7:
            return {
                'category': 'clinical_action',
                'category_cn': '需要临床行动',
                'icon': '🔴',
                'urgency': 'high',
                'description': f'致病性变异，{inheritance["pattern_name"]}遗传模式，建议尽快就医咨询。'
            }

        if inheritance.get('carrier_status'):
            return {
                'category': 'carrier_status',
                'category_cn': '携带者状态',
                'icon': '🟡',
                'urgency': 'low',
                'description': '携带者状态，通常不发病，但生育前建议伴侣筛查。'
            }

        if score['total_score'] >= 5:
            return {
                'category': 'disease_risk',
                'category_cn': '疾病风险',
                'icon': '🟠',
                'urgency': 'medium',
                'description': '风险因素或复杂遗传关联，建议结合临床表现评估。'
            }

        return {
            'category': 'research_vus',
            'category_cn': '研究意义不明',
            'icon': '⚪',
            'urgency': 'none',
            'description': '证据不足，暂无临床意义。'
        }


class ActionabilityEngine:
    @classmethod
    def assess(cls, category: str, gene_symbol: str, disease_name: str) -> Dict:
        actions = []

        if category == 'clinical_action':
            actions.extend([
                '尽快预约遗传咨询专科',
                '告知直系亲属，建议家族筛查',
                '建立专科随访档案',
            ])
            if 'cancer' in (disease_name or '').lower() or 'tumor' in (disease_name or '').lower():
                actions.append('根据指南启动早期筛查方案')
            if 'pancreatitis' in (disease_name or '').lower():
                actions.extend(['严格禁酒', '避免高脂饮食', '定期检测淀粉酶/脂肪酶'])

        elif category == 'pharmacogenomics':
            actions.extend([
                '携带此报告就诊时主动告知医生',
                '开始新药物前查询药物基因组指南',
                '避免自行调整药物剂量',
            ])

        elif category == 'carrier_status':
            actions.extend([
                '伴侣如有生育计划，建议进行携带者筛查',
                '了解该疾病的产前诊断选项',
                '保持常规健康体检',
            ])

        elif category == 'disease_risk':
            actions.extend([
                '结合个人和家族病史综合评估',
                '保持定期体检',
                '关注相关症状的早期表现',
            ])

        return {
            'actions': actions,
            'follow_up': '建议6-12个月复查医学知识库更新',
            'genetic_counseling_recommended': category in ('clinical_action', 'carrier_status'),
        }


class ReasoningEngine:
    @classmethod
    def analyze(cls, variant: Dict, genotype: str, user_profile: Optional[Dict] = None) -> Dict:
        gene_symbol = variant.get('gene_symbol') or variant.get('gene_name', '未知')
        significance = variant.get('clinvar_significance', '')

        inheritance = variant.get('inheritance_pattern', '')
        if not inheritance and gene_symbol != '未知':
            inheritance = cls._infer_inheritance(gene_symbol)

        zygosity = cls._genotype_to_zygosity(genotype)

        inh_result = InheritanceRule.assess(inheritance, zygosity, significance)
        score = EvidenceScorer.score(variant, inh_result)
        risk = RiskClassifier.classify(variant, score, inh_result)
        action = ActionabilityEngine.assess(risk['category'], gene_symbol, variant.get('disease', ''))

        personal = None
        if user_profile:
            personal = cls._match_phenotype(variant, user_profile)

        finding = {
            'variant_id': variant.get('id'),
            'chrom': variant.get('chromosome'),
            'pos': variant.get('position'),
            'ref': variant.get('reference'),
            'alt': variant.get('alternate'),
            'gene_symbol': gene_symbol,
            'genotype': genotype,
            'zygosity': zygosity,
            'clinvar_significance': significance,
            'disease': variant.get('disease', ''),
            'inheritance': inh_result,
            'score': score,
            'category': risk['category'],
            'category_cn': risk['category_cn'],
            'icon': risk['icon'],
            'urgency': risk['urgency'],
            'description': risk['description'],
            'actionability': action,
            'personal_context': personal,
            'recommendations': action['actions'],
        }

        return finding

    @staticmethod
    def _genotype_to_zygosity(gt: str) -> str:
        if gt in ('0/1', '0|1', '1/0', '1|1'):
            return 'heterozygous'
        if gt in ('1/1', '1|1'):
            return 'homozygous'
        if gt in ('1', '0') or gt == './1':
            return 'hemizygous'
        return 'unknown'

    @staticmethod
    def _infer_inheritance(gene_symbol: str) -> str:
        ad_genes = {'PRSS1', 'BRCA1', 'BRCA2', 'APOE', 'CFTR', 'F5'}
        ar_genes = {'NAGLU', 'DPYD', 'MTHFR'}
        if gene_symbol in ad_genes:
            return 'AD'
        if gene_symbol in ar_genes:
            return 'AR'
        return ''

    @staticmethod
    def _match_phenotype(variant: Dict, profile: Dict) -> Optional[Dict]:
        conditions = profile.get('conditions', [])
        family = profile.get('family_history', [])

        modifier = 0
        matched = []
        disease = (variant.get('disease') or '').lower()

        for cond in conditions:
            if cond.lower() in disease or any(word in disease for word in cond.lower().split()):
                modifier += 2
                matched.append(f'个人病史: {cond}')

        for fh in family:
            relation = fh.get('relation', '')
            cond = fh.get('condition', '')
            if cond.lower() in disease or any(word in disease for word in cond.lower().split()):
                modifier += 1
                matched.append(f'家族史: {relation}有{cond}')

        if matched:
            return {
                'risk_modifier': modifier,
                'matched_factors': matched,
                'assessment': '个人/家族病史与基因关联疾病有重叠，建议重点关注。'
            }
        return None
""",

    'pipeline/__init__.py': '',

    'pipeline/import_clinvar.py': r"""#!/usr/bin/env python3
import gzip
import sys
import re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from database.db import init_db, GeneRepository, DiseaseRepository, VariantRepository, VariantDiseaseRepository


def parse_geneinfo(info: str) -> list:
    match = re.search(r'GENEINFO=([^;]+)', info)
    if not match:
        return []
    genes = []
    for part in match.group(1).split('|'):
        if ':' in part:
            symbol, gid = part.split(':', 1)
            genes.append((symbol.strip(), gid.strip()))
    return genes


def parse_clnsig(info: str) -> str:
    match = re.search(r'CLNSIG=([^;]+)', info)
    return match.group(1) if match else None


def parse_clnrevstat(info: str) -> str:
    match = re.search(r'CLNREVSTAT=([^;]+)', info)
    return match.group(1).replace('_', ' ') if match else None


def parse_clndn(info: str) -> list:
    match = re.search(r'CLNDN=([^;]+)', info)
    if not match:
        return []
    raw = match.group(1)
    diseases = []
    for d in raw.split('|'):
        d = d.strip()
        if d and d != 'not_provided':
            d = d.replace('\\\\', '').replace('_', ' ')
            diseases.append(d)
    return diseases


def parse_rs(info: str) -> str:
    match = re.search(r'RS=([^;]+)', info)
    return match.group(1) if match else None


def parse_variation_id(info: str) -> str:
    match = re.search(r'CLNVCID=([^;]+)', info)
    if not match:
        match = re.search(r'CLNVI=([^;]+)', info)
    return match.group(1) if match else None


def parse_hgvs(info: str) -> dict:
    result = {}
    m = re.search(r'CLNHGVS=([^;]+)', info)
    if m:
        result['genomic'] = m.group(1)
    return result


def import_clinvar(vcf_path: str, max_records: int = None):
    init_db()
    open_fn = gzip.open if vcf_path.endswith('.gz') else open
    imported = 0

    print(f"Importing {vcf_path}...")

    with open_fn(vcf_path, 'rt', encoding='utf-8', errors='ignore') as f:
        for line in f:
            if line.startswith('#'):
                continue
            fields = line.strip().split('\t')
            if len(fields) < 8:
                continue

            chrom = fields[0].replace('chr', '').replace('Chr', '')
            pos = int(fields[1])
            ref = fields[3]
            alt = fields[4]
            info = fields[7]

            gene_symbols = parse_geneinfo(info)
            gene_id = None
            if gene_symbols:
                sym, ensembl = gene_symbols[0]
                gene_id = GeneRepository.upsert(symbol=sym, ensembl_id=ensembl)

            sig = parse_clnsig(info)
            revstat = parse_clnrevstat(info)
            rs = parse_rs(info)
            var_id = parse_variation_id(info)
            hgvs = parse_hgvs(info)

            if not sig:
                continue

            variant_db_id = VariantRepository.upsert(
                chrom=chrom, pos=pos, ref=ref, alt=alt,
                gene_id=gene_id,
                hgvs_genomic=hgvs.get('genomic'),
                clinvar_significance=sig,
                clinvar_review_status=revstat,
                dbsnp_id=rs,
                clinvar_variation_id=var_id,
                raw_info=info[:2000]
            )

            diseases = parse_clndn(info)
            for dname in diseases:
                if not dname or dname.lower() in ('not specified', 'see cases', 'not provided'):
                    continue
                did = DiseaseRepository.upsert(name=dname)
                VariantDiseaseRepository.link(
                    variant_db_id, did,
                    significance=sig,
                    evidence_level=revstat
                )

            imported += 1
            if imported % 5000 == 0:
                print(f"  Imported {imported} variants...")

            if max_records and imported >= max_records:
                break

    print(f"Done. Imported {imported} variants.")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python import_clinvar.py <clinvar.vcf.gz> [max_records]")
        sys.exit(1)
    vcf = sys.argv[1]
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else None
    import_clinvar(vcf, limit)
""",

    'templates/index.html': r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>DNA Genome Intelligence v2</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;background:#0b1120;color:#e2e8f0;line-height:1.6}
.container{max-width:800px;margin:0 auto;padding:48px 20px}
h1{font-size:32px;margin-bottom:8px;background:linear-gradient(90deg,#60a5fa,#a78bfa);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.subtitle{color:#64748b;margin-bottom:40px}
.card{background:#151e32;border-radius:16px;padding:24px;margin-bottom:16px;border:1px solid #1e293b}
.card-title{font-size:15px;font-weight:600;margin-bottom:12px;display:flex;align-items:center;gap:8px}
.required{color:#ef4444}
.optional{background:#1e293b;color:#64748b;font-size:11px;padding:2px 8px;border-radius:10px;margin-left:auto}
.dropzone{border:2px dashed #334155;border-radius:12px;padding:32px;text-align:center;cursor:pointer;transition:all .2s}
.dropzone:hover{border-color:#60a5fa;background:#1e293b}
.dropzone input{display:none}
.file-name{margin-top:8px;font-size:13px;color:#60a5fa}
.btn{width:100%;padding:14px;background:linear-gradient(90deg,#3b82f6,#8b5cf6);border:none;border-radius:12px;color:#fff;font-size:16px;font-weight:600;cursor:pointer;margin-top:8px}
.btn:hover{opacity:.9}
.btn:disabled{opacity:.5;cursor:not-allowed}
.status{margin-top:16px;padding:12px;border-radius:8px;font-size:14px;display:none}
.status.success{background:#064e3b;color:#6ee7b7;display:block}
.status.error{background:#450a0a;color:#fca5a5;display:block}
textarea{width:100%;background:#0f172a;border:1px solid #334155;border-radius:8px;padding:12px;color:#e2e8f0;font-family:monospace;font-size:13px;resize:vertical}
.hint{font-size:12px;color:#64748b;margin-top:6px}
.row{display:grid;grid-template-columns:1fr 1fr;gap:12px}
@media(max-width:600px){.row{grid-template-columns:1fr}}
</style>
</head>
<body>
<div class="container">
<h1>DNA Genome Intelligence v2.0</h1>
<p class="subtitle">知识图谱驱动 · 规则推理引擎 · 个人健康智能</p>
<form id="uploadForm" enctype="multipart/form-data">
<div class="card">
<div class="card-title">📄 VCF 基因文件 <span class="required">*</span></div>
<div class="dropzone" onclick="this.querySelector('input').click()">
<input type="file" name="vcf" accept=".vcf,.vcf.gz" onchange="showFile(this)">
<div>点击或拖拽上传 .vcf / .vcf.gz</div>
<div class="file-name"></div>
</div>
</div>
<div class="card">
<div class="card-title">👤 个人健康档案 <span class="optional">可选</span></div>
<div class="dropzone" onclick="this.querySelector('input').click()">
<input type="file" name="profile" accept=".json" onchange="showFile(this)">
<div>上传 profile.json</div>
<div class="file-name"></div>
</div>
<p class="hint">或直接粘贴 JSON：</p>
<textarea name="profile_json" rows="4" placeholder='{"basic":{"age":38,"sex":"female"},"conditions":["anxiety"],"family_history":[{"condition":"pancreatitis","relation":"father"}]}'></textarea>
</div>
<div class="card">
<div class="card-title">⚙️ 分析参数</div>
<div class="row">
<div>
<label style="font-size:13px;color:#94a3b8">最大变异数</label>
<input type="number" name="max_variants" value="10000" style="width:100%;margin-top:6px;padding:10px;background:#0f172a;border:1px solid #334155;border-radius:8px;color:#e2e8f0">
</div>
<div>
<label style="font-size:13px;color:#94a3b8">最低评分</label>
<input type="number" name="min_score" value="0" style="width:100%;margin-top:6px;padding:10px;background:#0f172a;border:1px solid #334155;border-radius:8px;color:#e2e8f0">
</div>
</div>
</div>
<button type="submit" class="btn" id="submitBtn">开始分析</button>
<div id="status" class="status"></div>
</form>
</div>
<script>
function showFile(input){
var names=Array.from(input.files).map(function(f){return f.name}).join(", ");
input.parentElement.querySelector(".file-name").textContent=names||"";
}
document.getElementById("uploadForm").onsubmit=function(e){
e.preventDefault();
var btn=document.getElementById("submitBtn"),status=document.getElementById("status");
btn.disabled=true;btn.textContent="分析中...";status.className="status";
fetch("/api/analyze",{method:"POST",body:new FormData(e.target)}).then(function(res){return res.json()}).then(function(data){
if(data.success){status.className="status success";status.textContent="分析完成！共发现 "+data.reported+" 条相关变异。正在跳转...";setTimeout(function(){window.open(data.redirect,"_blank")},800);}
else{status.className="status error";status.textContent=data.error||"分析失败";}
}).catch(function(err){status.className="status error";status.textContent=err.message;});
btn.disabled=false;btn.textContent="开始分析";
};
</script>
</body>
</html>""",

    'web_api_v2.py': r"""#!/usr/bin/env python3
import json, sys, gzip
from pathlib import Path
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename

BASE = Path(__file__).parent
sys.path.insert(0, str(BASE))

from database.db import init_db, UserGenotypeRepository
from engine.knowledge_service import KnowledgeService
from engine.reasoning_engine import ReasoningEngine

app = Flask(__name__, template_folder=str(BASE / "templates"))
UPLOAD = BASE / "uploads"
REPORT = BASE / "reports"
UPLOAD.mkdir(exist_ok=True)
REPORT.mkdir(exist_ok=True)
app.config["MAX_CONTENT_LENGTH"] = 500 * 1024 * 1024

init_db()


def parse_vcf(vcf_path: str, max_variants: int = None):
    open_fn = gzip.open if vcf_path.endswith('.gz') else open
    variants = []
    with open_fn(vcf_path, 'rt', encoding='utf-8', errors='ignore') as f:
        for line in f:
            if line.startswith('#'):
                continue
            fields = line.strip().split('\t')
            if len(fields) < 8:
                continue
            gt = None
            if len(fields) > 9:
                fmt = fields[8].split(':')
                if 'GT' in fmt and len(fields) > 9:
                    vals = fields[9].split(':')
                    gt_idx = fmt.index('GT')
                    if gt_idx < len(vals):
                        gt = vals[gt_idx]
            variants.append({
                'chrom': fields[0].replace('chr', '').replace('Chr', ''),
                'pos': int(fields[1]),
                'ref': fields[3],
                'alt': fields[4],
                'id': fields[2],
                'info': fields[7],
                'genotype': gt,
            })
            if max_variants and len(variants) >= max_variants:
                break
    return variants


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/analyze", methods=["POST"])
def analyze_api():
    vcf = request.files.get("vcf")
    if not vcf or vcf.filename == "":
        return jsonify({"error": "请上传VCF文件"}), 400
    vcf_path = UPLOAD / secure_filename(vcf.filename)
    vcf.save(vcf_path)

    profile = None
    if request.files.get("profile"):
        p = UPLOAD / secure_filename(request.files["profile"].filename)
        request.files["profile"].save(p)
        try:
            profile = json.load(open(p, encoding='utf-8'))
        except Exception:
            pass
    elif request.form.get("profile_json"):
        try:
            profile = json.loads(request.form["profile_json"])
        except Exception:
            pass

    max_v = request.form.get("max_variants", type=int) or 10000
    min_s = request.form.get("min_score", 0, type=int)

    raw_variants = parse_vcf(str(vcf_path), max_v)
    total = len(raw_variants)
    findings = []
    sample_name = secure_filename(vcf.filename).split('.')[0]

    for v in raw_variants:
        kg_variant = KnowledgeService.get_variant(v['chrom'], v['pos'], v['ref'], v['alt'])
        if not kg_variant:
            continue
        finding = ReasoningEngine.analyze(kg_variant, v['genotype'], profile)
        if finding['score']['total_score'] >= min_s and finding['category'] != 'research_vus':
            findings.append(finding)
            if kg_variant.get('id'):
                UserGenotypeRepository.save(sample_name, kg_variant['id'], v['genotype'] or './.')

    order = {'clinical_action': 0, 'pharmacogenomics': 1, 'disease_risk': 2, 'carrier_status': 3}
    findings.sort(key=lambda x: (order.get(x.get('category', ''), 99), -x['score']['total_score']))

    results = {
        "total_vcf_variants": total,
        "reported": len(findings),
        "findings": findings,
        "profile": profile,
        "timestamp": datetime.now().isoformat(),
    }

    json_path = REPORT / "report_v2.json"
    json.dump(results, open(json_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)

    html_path = REPORT / "report_v2.html"
    html_path.write_text(generate_html_report(results), encoding='utf-8')

    return jsonify({"success": True, "reported": len(findings), "redirect": "/reports/report_v2.html"})


def generate_html_report(data: dict) -> str:
    findings = data.get('findings', [])
    cats = {}
    for f in findings:
        c = f.get('category_cn', '其他')
        cats[c] = cats.get(c, 0) + 1

    cards_html = []
    for f in findings:
        gene = f.get('gene_symbol', '未知')
        score = f['score']['total_score']
        urgency_color = {'high': '#ef4444', 'medium': '#f97316', 'low': '#eab308', 'none': '#64748b'}
        color = urgency_color.get(f.get('urgency', 'none'), '#64748b')
        actions = ''.join('<li style="margin:6px 0">%s</li>' % a for a in f.get('recommendations', []))

        personal_block = ''
        if f.get('personal_context'):
            personal_block = '<div style="margin-top:12px;padding:12px;background:#1e293b;border-radius:8px;border-left:3px solid #60a5fa">'
            personal_block += '<strong style="color:#60a5fa">👤 个人化评估：</strong>'
            personal_block += '<p style="margin-top:6px">%s</p></div>' % f["personal_context"]["assessment"]

        card = '<div style="background:#151e32;border-radius:16px;padding:24px;margin-bottom:16px;border:1px solid #1e293b">'
        card += '<div style="display:flex;align-items:center;gap:12px;margin-bottom:12px">'
        card += '<span style="font-size:24px">%s</span>' % f.get("icon","")
        card += '<div><div style="font-size:18px;font-weight:600">%s</div>' % gene
        card += '<div style="font-size:13px;color:#64748b">Chr%s:%s · %s→%s · %s</div></div>' % (
            f.get("chrom",""), f.get("pos",""), f.get("ref",""), f.get("alt",""), f.get("zygosity",""))
        card += '<div style="margin-left:auto;text-align:right">'
        card += '<div style="font-size:24px;font-weight:700;color:%s">%s</div>' % (color, score)
        card += '<div style="font-size:11px;color:#64748b">证据分</div></div></div>'
        card += '<div style="display:flex;gap:8px;margin-bottom:12px;flex-wrap:wrap">'
        card += '<span style="background:#1e293b;padding:4px 12px;border-radius:20px;font-size:12px">%s</span>' % f.get("category_cn","")
        card += '<span style="background:#1e293b;padding:4px 12px;border-radius:20px;font-size:12px">%s</span>' % f.get("clinvar_significance","")
        card += '<span style="background:#1e293b;padding:4px 12px;border-radius:20px;font-size:12px">%s</span>' % f.get("inheritance",{}).get("pattern_name","")
        card += '</div>'
        card += '<p style="color:#94a3b8;font-size:14px;line-height:1.6">%s</p>' % f.get("description","")
        card += '<div style="margin-top:12px"><strong style="color:#e2e8f0;font-size:13px">建议行动：</strong>'
        card += '<ul style="color:#94a3b8;font-size:13px;margin-top:6px;padding-left:20px">%s</ul></div>' % actions
        card += personal_block
        card += '</div>'
        cards_html.append(card)

    summary_html = []
    cat_colors = {"需要临床行动": "#ef4444", "药物基因组学": "#3b82f6", "疾病风险": "#f97316", "携带者状态": "#eab308"}
    for c, n in cats.items():
        summary_html.append('<div style="flex:1;background:#151e32;border-radius:16px;padding:20px;text-align:center;border:1px solid #1e293b;min-width:140px">')
        summary_html.append('<div style="font-size:32px;font-weight:700;color:%s">%s</div>' % (cat_colors.get(c, "#64748b"), n))
        summary_html.append('<div style="font-size:13px;color:#64748b;margin-top:4px">%s</div></div>' % c)

    page = []
    page.append('<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8">')
    page.append('<meta name="viewport" content="width=device-width,initial-scale=1.0">')
    page.append('<title>DNA Report v2.0</title>')
    page.append('<style>body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;background:#0b1120;color:#e2e8f0;margin:0;padding:0}')
    page.append('.container{max-width:900px;margin:0 auto;padding:40px 20px}')
    page.append('h1{font-size:28px;margin-bottom:8px}')
    page.append('.subtitle{color:#64748b;margin-bottom:32px;font-size:14px}')
    page.append('.summary{display:flex;gap:12px;margin-bottom:32px;flex-wrap:wrap}</style>')
    page.append('</head><body><div class="container">')
    page.append('<h1>🧬 个人基因组智能报告</h1>')
    page.append('<p class="subtitle">知识图谱版本 · %s · 共分析 %s 个变异</p>' % (data.get("timestamp","")[:10], data.get("total_vcf_variants",0)))
    page.append('<div class="summary">%s</div>' % ''.join(summary_html))
    page.append(''.join(cards_html))
    page.append('<div style="margin-top:40px;padding:20px;background:#151e32;border-radius:12px;border:1px solid #1e293b;font-size:12px;color:#64748b;text-align:center">')
    page.append('<p>⚠️ 本报告仅供教育和研究参考，不能替代专业医疗建议。</p>')
    page.append('<p style="margin-top:8px">DNA Personal Genome Intelligence v2.0 · 基于 ClinVar 知识图谱</p>')
    page.append('</div></div></body></html>')

    return ''.join(page)


@app.route("/reports/<path:filename>")
def serve_report(filename):
    return send_from_directory(REPORT, filename)


@app.route("/api/report")
def report_api():
    r = REPORT / "report_v2.json"
    if r.exists():
        return jsonify(json.load(open(r, encoding='utf-8')))
    return jsonify({"findings": []})


if __name__ == "__main__":
    print("=" * 50)
    print("🧬 DNA Genome Intelligence v2.0")
    print("知识图谱 + 规则推理引擎")
    print("打开浏览器访问: http://localhost:5000")
    print("=" * 50)
    app.run(debug=True, port=5000)
""",

    'launch.sh': r"""#!/usr/bin/env bash
cd "$(dirname "$0")"
python3 -c "import flask" 2>/dev/null || python3 -m pip install flask
python3 -c "from database.db import init_db; init_db()"
if [ -n "$1" ]; then
    echo "Importing ClinVar: $1"
    python3 pipeline/import_clinvar.py "$1"
fi
echo ""
echo "========================================"
echo "🧬 DNA Genome Intelligence v2.0"
echo "Knowledge Graph + Reasoning Engine"
echo "Open: http://localhost:5000"
echo "========================================"
python3 web_api_v2.py
""",

    'README_v2.md': r"""# DNA Personal Genome Intelligence v2.0

## 架构升级

从 v0.4 的 JSON 文件驱动 → **SQLite 知识图谱 + 规则推理引擎**

```
VCF
  ↓
ClinVar Knowledge Graph (SQLite)
  ↓
Knowledge Service (统一查询接口)
  ↓
Reasoning Engine (继承/证据/风险/行动规则)
  ↓
Personalized Report
```

## 快速开始

### 1. 导入 ClinVar 知识库

```bash
python3 pipeline/import_clinvar.py data/clinical_clinvar_full.vcf.gz
```

### 2. 启动 Web 服务

```bash
bash launch.sh
# 或
python3 web_api_v2.py
```

### 3. 访问

打开浏览器：**http://localhost:5000**

## 核心改进

| v0.4 | v2.0 |
|------|------|
| 手写 JSON 知识库 | ClinVar 自动导入 SQLite |
| 硬编码疾病描述 | 数据库关联 + 推理生成 |
| ANNParser 依赖 SnpEff | 直接解析 ClinVar 原生格式 |
| 评分逻辑简单 | 多维度规则引擎 |
| 无个人上下文 | Phenotype 匹配 + 家族史关联 |
| 结果经常为 0 | 只要 ClinVar 有记录就能匹配 |
""",
}


def main():
    base = Path(__file__).parent
    for path, content in FILES.items():
        fpath = base / path
        fpath.parent.mkdir(parents=True, exist_ok=True)
        fpath.write_text(content, encoding='utf-8')
        print(f'Created {path}')
    print('\n✅ DNA v2.0 架构文件创建完成')
    print('下一步: bash launch.sh')


if __name__ == '__main__':
    main()
