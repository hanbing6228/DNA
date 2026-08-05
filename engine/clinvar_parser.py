import re

class ClinVarParser:
    """ClinVar 字段解析器"""

    SIGNIFICANCE_MAP = {
        'Pathogenic': 'pathogenic',
        'Likely_pathogenic': 'likely_pathogenic',
        'Pathogenic/Likely_pathogenic': 'pathogenic',
        'Benign': 'benign',
        'Likely_benign': 'likely_benign',
        'Benign/Likely_benign': 'benign',
        'Uncertain_significance': 'vus',
        'Conflicting_interpretations_of_pathogenicity': 'conflicting',
        'drug_response': 'drug_response',
        'risk_factor': 'risk_factor',
        'protective': 'protective',
        'not_provided': 'not_provided',
        'other': 'other',
        'Affects': 'affects',
        'association': 'association',
    }

    REVIEW_WEIGHTS = {
        'practice_guideline': 7,
        'reviewed_by_expert_panel': 6,
        'criteria_provided': 3,
        'multiple_submitters': 4,
        'no_conflicts': 3,
        'single_submitter': 1,
        'no_assertion': 0,
        'no_criteria': 0,
    }

    @classmethod
    def parse(cls, info_field):
        result = {}

        clnsig = re.search(r'CLNSIG=([^;]+)', info_field)
        if clnsig:
            raw = clnsig.group(1)
            result['significance_raw'] = raw
            result['significance'] = cls.SIGNIFICANCE_MAP.get(raw, raw.lower().replace(' ', '_'))

        clndn = re.search(r'CLNDN=([^;]+)', info_field)
        if clndn:
            result['disease'] = clndn.group(1).replace('_', ' ').replace('|', ', ')

        clnrev = re.search(r'CLNREVSTAT=([^;]+)', info_field)
        if clnrev:
            raw_rev = clnrev.group(1)
            result['review_status_raw'] = raw_rev
            result['review_score'] = cls._score_review(raw_rev)

        clnsigconf = re.search(r'CLNSIGCONF=([^;]+)', info_field)
        if clnsigconf:
            result['conflicting'] = clnsigconf.group(1)

        allele_id = re.search(r'CLNALLELEID=([^;]+)', info_field)
        if allele_id:
            result['allele_id'] = allele_id.group(1)

        clnhgvs = re.search(r'CLNHGVS=([^;]+)', info_field)
        if clnhgvs:
            result['cln_hgvs'] = clnhgvs.group(1)

        return result

    @classmethod
    def _score_review(cls, review_str):
        score = 0
        review_lower = review_str.lower()
        for key, weight in cls.REVIEW_WEIGHTS.items():
            if key.replace('_', ' ') in review_lower or key in review_lower:
                score = max(score, weight)
        return score

    @classmethod
    def is_pathogenic(cls, data):
        return data.get('significance') in ('pathogenic', 'likely_pathogenic')

    @classmethod
    def is_drug_response(cls, data):
        return data.get('significance') == 'drug_response'
