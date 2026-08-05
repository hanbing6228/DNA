import json
from pathlib import Path

class ActionabilityEngine:
    """可操作性评估引擎"""

    def __init__(self, diseases_path="knowledge/diseases.json", drugs_path="knowledge/drugs.json"):
        self.diseases = {}
        self.drugs = {}

        dpath = Path(diseases_path)
        if dpath.exists():
            with open(dpath, 'r', encoding='utf-8') as f:
                self.diseases = json.load(f).get('diseases', {})

        drugpath = Path(drugs_path)
        if drugpath.exists():
            with open(drugpath, 'r', encoding='utf-8') as f:
                self.drugs = json.load(f).get('genes', {})

    def assess(self, variant_data):
        gene = variant_data.get('gene_name', '')
        disease = variant_data.get('disease', '')
        category = variant_data.get('category', '')
        inheritance = variant_data.get('inheritance_assessment', {})

        result = {
            'actionable': False,
            'urgency': 'low',
            'when_to_act': '常规体检时提及',
            'actions': [],
            'surveillance': [],
            'lifestyle': [],
            'drug_guidance': [],
            'specialist_referral': None,
        }

        # 药物基因组学
        if category == 'pharmacogenomics':
            drug_info = self.drugs.get(gene, {})
            result['actionable'] = True
            result['urgency'] = 'medium'
            result['when_to_act'] = '用药前'
            result['actions'].append('与开药医生分享此基因结果')
            result['actions'].append('可能需要调整药物剂量或选择替代药物')

            for drug in drug_info.get('drugs', []):
                result['drug_guidance'].append({
                    'drug': drug['name'],
                    'effect': drug['effect'],
                    'action': drug['action'],
                })

            guideline = drug_info.get('clinical_guideline', '')
            if guideline:
                result['actions'].append(f"临床指南：{guideline}")

            return result

        # 疾病相关
        if disease:
            disease_info = self._get_disease_info(disease)

            if disease_info.get('actionable', False):
                result['actionable'] = True
                result['urgency'] = 'high' if disease_info.get('severity') == 'high' else 'medium'
                result['when_to_act'] = '尽快咨询专科医生'
                result['surveillance'] = disease_info.get('surveillance', [])
                result['actions'].append('建议遗传咨询')
                result['actions'].append('与医生讨论筛查方案')

                if disease_info.get('severity') == 'high':
                    result['specialist_referral'] = '遗传科/专科'
            else:
                result['when_to_act'] = '常规体检时提及'
                result['actions'].append('目前无特殊临床行动需要')

        # 携带者
        if inheritance.get('carrier_status') and not inheritance.get('affected_status'):
            result['actions'].append('生育前建议伴侣进行携带者筛查')
            result['lifestyle'].append('保持健康生活方式')
            result['lifestyle'].append('定期体检')

        # 已发病风险
        if inheritance.get('affected_status'):
            result['lifestyle'].append('避免已知风险因素')
            result['lifestyle'].append('建立专科随访')
            if inheritance.get('penetrance', 1.0) < 0.5:
                result['actions'].append('注意：该变异外显率较低，需结合临床表现')

        return result

    def _get_disease_info(self, disease_name):
        for key, info in self.diseases.items():
            if key.lower() in disease_name.lower() or disease_name.lower() in key.lower():
                return info
        return {}
