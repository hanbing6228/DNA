#!/usr/bin/env python3
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
