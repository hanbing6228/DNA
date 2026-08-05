import json
from pathlib import Path

class MedicationEngine:
    """药物基因组学引擎"""

    def __init__(self, drugs_path="knowledge/drugs.json"):
        self.drugs = {}
        path = Path(drugs_path)
        if path.exists():
            with open(path, 'r', encoding='utf-8') as f:
                self.drugs = json.load(f).get('genes', {})

    def get_drug_guidance(self, gene_name):
        return self.drugs.get(gene_name, {})

    def format_passport(self, variant_data):
        """生成药物护照条目"""
        gene = variant_data.get('gene_name', '')
        guidance = self.get_drug_guidance(gene)

        if not guidance:
            return None

        drugs = guidance.get('drugs', [])
        star_allele = guidance.get('star_allele', '')

        return {
            'gene': gene,
            'star_allele': star_allele,
            'drugs': drugs,
            'guideline': guidance.get('clinical_guideline', ''),
            'phenotype': variant_data.get('clinvar_significance', ''),
        }
