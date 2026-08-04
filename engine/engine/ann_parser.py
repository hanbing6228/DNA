import re

class ANNParser:
    """Parse SnpEff ANN field from VCF INFO."""

    # ANN format: Allele | Annotation | Annotation_Impact | Gene_Name | Gene_ID | 
    #             Feature_Type | Feature_ID | Transcript_BioType | Rank | HGVS.c | HGVS.p | 
    #             cDNA.pos/cDNA.length | CDS.pos/CDS.length | AA.pos/AA.length | Distance | 
    #             ERRORS/WARNINGS/INFO

    @staticmethod
    def parse(info_field):
        """Extract ANN annotations from INFO field."""
        annotations = []

        if 'ANN=' not in info_field:
            return annotations

        # Extract ANN value
        ann_match = re.search(r'ANN=([^;]+)', info_field)
        if not ann_match:
            return annotations

        ann_raw = ann_match.group(1)

        # Split by comma for multiple transcripts
        for transcript in ann_raw.split(','):
            parts = transcript.split('|')
            if len(parts) < 10:
                continue

            ann = {
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
            }
            annotations.append(ann)

        return annotations

    @staticmethod
    def get_most_severe(annotations):
        """Get the most severe impact annotation."""
        if not annotations:
            return None

        impact_order = {'HIGH': 3, 'MODERATE': 2, 'LOW': 1, 'MODIFIER': 0}

        sorted_anns = sorted(
            annotations,
            key=lambda x: impact_order.get(x.get('impact', 'MODIFIER'), 0),
            reverse=True
        )
        return sorted_anns[0]
