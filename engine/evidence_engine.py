class EvidenceEngine:
    """证据评分引擎"""

    IMPACT_SCORES = {'HIGH': 10, 'MODERATE': 5, 'LOW': 2, 'MODIFIER': 0}

    SIGNIFICANCE_SCORES = {
        'pathogenic': 10,
        'likely_pathogenic': 8,
        'vus': 3,
        'conflicting': 2,
        'risk_factor': 6,
        'drug_response': 7,
        'association': 4,
        'affects': 3,
        'benign': 0,
        'likely_benign': 0,
        'protective': 0,
        'not_provided': 0,
        'other': 0,
    }

    @classmethod
    def score(cls, variant_data):
        score = 0
        factors = []

        # Impact
        impact = variant_data.get('impact', 'MODIFIER')
        impact_score = cls.IMPACT_SCORES.get(impact, 0)
        if impact_score > 0:
            score += impact_score
            factors.append(f"功能影响 {impact} (+{impact_score})")

        # ClinVar significance
        sig = variant_data.get('clinvar_significance', '')
        sig_score = cls.SIGNIFICANCE_SCORES.get(sig, 0)
        if sig_score > 0:
            score += sig_score
            factors.append(f"ClinVar {sig} (+{sig_score})")

        # Review status
        review_score = variant_data.get('review_score', 0)
        if review_score > 0:
            score += review_score
            factors.append(f"证据强度 (+{review_score})")

        # Inheritance adjustment
        inh_adj = variant_data.get('inheritance_adjustment', 0)
        score = max(0, score + inh_adj)
        if inh_adj != 0:
            factors.append(f"遗传模式调整 ({inh_adj:+d})")

        # Determine priority
        if score >= 15:
            priority = 'CRITICAL'
        elif score >= 10:
            priority = 'HIGH'
        elif score >= 5:
            priority = 'MODERATE'
        elif score > 0:
            priority = 'LOW'
        else:
            priority = 'NONE'

        return {
            'total_score': score,
            'priority': priority,
            'factors': factors,
        }
