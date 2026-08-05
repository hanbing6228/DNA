import re

class ANNParser:
    """SnpEff ANN 字段解析器"""

    IMPACT_ORDER = {'HIGH': 4, 'MODERATE': 3, 'LOW': 2, 'MODIFIER': 1}

    @staticmethod
    def parse(info_field):
        if 'ANN=' not in info_field:
            return []

        match = re.search(r'ANN=([^;]+)', info_field)
        if not match:
            return []

        annotations = []
        for transcript in match.group(1).split(','):
            parts = transcript.split('|')
            if len(parts) < 10:
                continue

            annotations.append({
                'allele': parts[0],
                'effect': parts[1],
                'impact': parts[2],
                'gene_name': parts[3],
                'gene_id': parts[4],
                'feature_type': parts[5],
                'feature_id': parts[6],
                'transcript_biotype': parts[7],
                'rank': parts[8],
                'hgvs_c': parts[9] if len(parts) > 9 else None,
                'hgvs_p': parts[10] if len(parts) > 10 else None,
                'cdna_pos': parts[11] if len(parts) > 11 else None,
                'cds_pos': parts[12] if len(parts) > 12 else None,
                'aa_pos': parts[13] if len(parts) > 13 else None,
                'distance': parts[14] if len(parts) > 14 else None,
            })

        return annotations

    @staticmethod
    def get_most_severe(annotations):
        if not annotations:
            return None
        return max(annotations, key=lambda x: ANNParser.IMPACT_ORDER.get(x.get('impact', 'MODIFIER'), 0))
