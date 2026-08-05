class RiskClassifier:
    """临床风险分类器"""

    CATEGORIES = {
        'clinical_action': {'cn': '需要临床行动', 'icon': '🔴', 'color': '#ef4444'},
        'disease_risk': {'cn': '疾病风险', 'icon': '🟠', 'color': '#f97316'},
        'pharmacogenomics': {'cn': '药物基因组学', 'icon': '💊', 'color': '#3b82f6'},
        'carrier_status': {'cn': '携带者状态', 'icon': '🟡', 'color': '#eab308'},
        'research_vus': {'cn': '研究/VUS', 'icon': '⚪', 'color': '#94a3b8'},
    }

    @classmethod
    def classify(cls, variant_data):
        sig = variant_data.get('clinvar_significance', '')
        impact = variant_data.get('impact', '')
        inheritance = variant_data.get('inheritance_assessment', {})
        drug_info = variant_data.get('drug_guidance', [])

        # 药物基因组学优先
        if sig == 'drug_response' or drug_info:
            return cls._make('pharmacogenomics', 'medium', '仅在用药时相关')

        # 临床行动：AD致病且可能发病
        if (inheritance.get('affected_status') and 
            inheritance.get('clinical_relevance') == 'disease_associated'):
            return cls._make('clinical_action', 'high', '尽快咨询医生')

        # 疾病风险：复杂遗传/风险因素
        if sig in ('risk_factor', 'association') or inheritance.get('clinical_relevance') == 'risk_factor':
            return cls._make('disease_risk', 'medium', '定期监测')

        # 携带者状态：AR杂合
        if (inheritance.get('carrier_status') and 
            not inheritance.get('affected_status') and
            inheritance.get('clinical_relevance') == 'carrier'):
            return cls._make('carrier_status', 'low', '生育规划时')

        # VUS / 研究
        if sig in ('vus', 'conflicting', 'not_provided', 'other') or impact == 'MODIFIER':
            return cls._make('research_vus', 'lowest', '无需行动')

        # 默认
        return cls._make('research_vus', 'lowest', '无需行动')

    @classmethod
    def _make(cls, cat, priority, timing):
        info = cls.CATEGORIES.get(cat, cls.CATEGORIES['research_vus'])
        return {
            'category': cat,
            'category_cn': info['cn'],
            'category_icon': info['icon'],
            'category_color': info['color'],
            'priority': priority,
            'action_timing': timing,
        }
