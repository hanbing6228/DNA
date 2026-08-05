import json
from pathlib import Path

class InheritanceEngine:
    """遗传模式推理引擎：根据遗传模式、合子性、外显率评估真实风险"""

    def __init__(self, knowledge_path="knowledge/inheritance.json"):
        path = Path(knowledge_path)
        self.db = {}
        if path.exists():
            with open(path, 'r', encoding='utf-8') as f:
                self.db = json.load(f).get('genes', {})

    def get_gene_info(self, gene_name):
        return self.db.get(gene_name, {})

    @staticmethod
    def parse_genotype(gt_str):
        """解析基因型 0/0, 0/1, 1/1, 0|1 等"""
        if not gt_str:
            return {"zygosity": "unknown", "has_variant": False, "alleles": 0}

        gt = str(gt_str).replace('|', '/')
        parts = gt.split('/')
        if len(parts) != 2:
            return {"zygosity": "unknown", "has_variant": False, "alleles": 0}

        a, b = parts[0], parts[1]
        if a == '0' and b == '0':
            return {"zygosity": "homozygous_ref", "has_variant": False, "alleles": 0}
        elif (a == '0' and b != '0') or (a != '0' and b == '0'):
            return {"zygosity": "heterozygous", "has_variant": True, "alleles": 1}
        elif a != '0' and b != '0':
            return {"zygosity": "homozygous_alt", "has_variant": True, "alleles": 2}
        else:
            return {"zygosity": "unknown", "has_variant": False, "alleles": 0}

    def assess(self, gene_name, genotype_str, clinvar_significance):
        """综合评估真实临床风险"""
        gene_info = self.get_gene_info(gene_name)
        zyg = self.parse_genotype(genotype_str)

        result = {
            "gene": gene_name,
            "inheritance": gene_info.get('inheritance', 'unknown'),
            "penetrance": gene_info.get('penetrance', 0.5),
            "penetrance_description": gene_info.get('penetrance_description', ''),
            "zygosity": zyg['zygosity'],
            "alleles": zyg['alleles'],
            "has_variant": zyg['has_variant'],
            "carrier_status": False,
            "affected_status": False,
            "score_adjustment": 0,
            "clinical_relevance": "unknown",
            "explanation": "",
            "reproductive_risk": False,
        }

        if not gene_info or not zyg['has_variant']:
            result['explanation'] = "未检测到致病变异或基因信息不足。"
            result['clinical_relevance'] = "not_applicable"
            return result

        inheritance = result['inheritance']
        is_pathogenic = clinvar_significance in ('pathogenic', 'likely_pathogenic')

        # 常染色体显性 (AD)
        if inheritance == 'AD':
            if zyg['alleles'] >= 1 and is_pathogenic:
                result['affected_status'] = True
                result['carrier_status'] = True
                result['clinical_relevance'] = 'disease_associated'
                result['score_adjustment'] = 5
                result['explanation'] = f"常染色体显性遗传。携带一个致病等位基因即可发病。外显率约{result['penetrance']*100:.0f}%。"
                result['reproductive_risk'] = True
                if result['penetrance'] < 0.5:
                    result['explanation'] += " 注意：该基因外显率较低，携带者不一定发病。"
            else:
                result['clinical_relevance'] = 'not_applicable'
                result['explanation'] = "未携带致病等位基因。"

        # 常染色体隐性 (AR)
        elif inheritance == 'AR':
            if zyg['alleles'] == 2 and is_pathogenic:
                result['affected_status'] = True
                result['carrier_status'] = True
                result['clinical_relevance'] = 'disease_associated'
                result['score_adjustment'] = 5
                result['explanation'] = f"纯合致病。常染色体隐性遗传，两个等位基因均携带致病变异。"
                result['reproductive_risk'] = True
            elif zyg['alleles'] == 1 and is_pathogenic:
                result['carrier_status'] = True
                result['affected_status'] = False
                result['clinical_relevance'] = 'carrier'
                result['score_adjustment'] = -4  # 大幅降低分数
                result['explanation'] = "杂合携带者。常染色体隐性遗传，单个致病等位基因通常不发病。建议生育前伴侣进行携带者筛查。"
                result['reproductive_risk'] = True
            else:
                result['clinical_relevance'] = 'not_applicable'
                result['explanation'] = "未携带致病等位基因。"

        # X连锁 (XL)
        elif inheritance in ('X-linked', 'XL', 'X-linked dominant', 'X-linked recessive'):
            result['clinical_relevance'] = 'disease_associated' if is_pathogenic else 'not_applicable'
            result['explanation'] = "X连锁遗传。需结合性别评估。"
            result['reproductive_risk'] = True

        # 复杂/多基因
        elif inheritance in ('complex', 'multifactorial', 'polygenic'):
            if zyg['alleles'] >= 1:
                result['carrier_status'] = True
                result['clinical_relevance'] = 'risk_factor'
                result['score_adjustment'] = 1
                result['explanation'] = f"风险因素变异。多基因/复杂遗传模式，单独不决定疾病。外显率约{result['penetrance']*100:.0f}%。"

        else:
            result['explanation'] = "遗传模式未知，无法准确评估。"

        return result
