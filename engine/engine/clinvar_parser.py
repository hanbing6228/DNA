import re

class ClinVarParser:
    """Parse ClinVar annotations from VCF INFO field."""

    CLNSIG_MAP = {
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
    }

    @staticmethod
    def parse(info_field):
        """Extract ClinVar fields from INFO."""
        result = {}

        # CLNSIG - Clinical significance
        clnsig_match = re.search(r'CLNSIG=([^;]+)', info_field)
        if clnsig_match:
            raw = clnsig_match.group(1)
            result['significance_raw'] = raw
            result['significance'] = ClinVarParser.CLNSIG_MAP.get(raw, raw.lower())

        # CLNDN - Disease name
        clndn_match = re.search(r'CLNDN=([^;]+)', info_field)
        if clndn_match:
            result['disease'] = clndn_match.group(1).replace('_', ' ')

        # CLNREVSTAT - Review status
        clnrev_match = re.search(r'CLNREVSTAT=([^;]+)', info_field)
        if clnrev_match:
            result['review_status'] = clnrev_match.group(1)

        # CLNSIGCONF - Conflicting interpretations
        clnsigconf_match = re.search(r'CLNSIGCONF=([^;]+)', info_field)
        if clnsigconf_match:
            result['conflicting'] = clnsigconf_match.group(1)

        # CLNALLELEID - Allele ID
        clnallele_match = re.search(r'CLNALLELEID=([^;]+)', info_field)
        if clnallele_match:
            result['allele_id'] = clnallele_match.group(1)

        return result

    @staticmethod
    def is_pathogenic(clinvar_data):
        """Check if variant is pathogenic or likely pathogenic."""
        sig = clinvar_data.get('significance', '')
        return sig in ('pathogenic', 'likely_pathogenic')

    @staticmethod
    def is_drug_response(clinvar_data):
        """Check if variant has drug response significance."""
        sig = clinvar_data.get('significance', '')
        return sig == 'drug_response'
