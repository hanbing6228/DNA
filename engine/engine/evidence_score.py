class EvidenceScorer:
    """Score variant evidence and priority."""

    IMPACT_SCORES = {
        'HIGH': 10,
        'MODERATE': 5,
        'LOW': 2,
        'MODIFIER': 0,
    }

    CLNSIG_SCORES = {
        'pathogenic': 10,
        'likely_pathogenic': 8,
        'vus': 4,
        'conflicting': 3,
        'risk_factor': 6,
        'drug_response': 7,
        'benign': 0,
        'likely_benign': 0,
        'protective': 0,
    }

    REVIEW_SCORES = {
        'practice_guideline': 5,
        'reviewed_by_expert_panel': 4,
        'multiple_submitters': 3,
        'single_submitter': 1,
        'no_conflicts': 2,
        'criteria_provided': 1,
        'no_assertion': 0,
    }

    @classmethod
    def score_variant(cls, variant_data):
        """Calculate overall evidence score for a variant."""
        score = 0
        factors = []

        # Impact score
        impact = variant_data.get('impact', 'MODIFIER')
        impact_score = cls.IMPACT_SCORES.get(impact, 0)
        if impact_score > 0:
            score += impact_score
            factors.append(f"Impact: {impact} (+{impact_score})")

        # ClinVar significance
        clnsig = variant_data.get('clinvar_significance', '')
        cln_score = cls.CLNSIG_SCORES.get(clnsig, 0)
        if cln_score > 0:
            score += cln_score
            factors.append(f"ClinVar: {clnsig} (+{cln_score})")

        # Review status
        review = variant_data.get('review_status', '')
        rev_score = 0
        for key, val in cls.REVIEW_SCORES.items():
            if key in review.lower():
                rev_score = max(rev_score, val)
        if rev_score > 0:
            score += rev_score
            factors.append(f"Review: {review} (+{rev_score})")

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
