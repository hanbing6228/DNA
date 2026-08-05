import gzip
from pathlib import Path

class VCFParser:
    """VCF/VCF.GZ 解析器"""

    @staticmethod
    def parse(filepath):
        variants = []
        header_lines = []
        sample_names = []

        open_fn = gzip.open if str(filepath).endswith('.gz') else open

        with open_fn(filepath, 'rt', encoding='utf-8', errors='ignore') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                if line.startswith('##'):
                    header_lines.append(line)
                    continue
                if line.startswith('#CHROM'):
                    parts = line.split('\t')
                    if len(parts) > 9:
                        sample_names = parts[9:]
                    continue
                if line.startswith('#'):
                    continue

                fields = line.split('\t')
                if len(fields) < 8:
                    continue

                # Parse genotype if available
                genotype = None
                sample_data = {}
                if len(fields) > 9:
                    format_col = fields[8]
                    format_keys = format_col.split(':')
                    for i, sample_col in enumerate(fields[9:]):
                        sample_values = sample_col.split(':')
                        sample_data[sample_names[i] if i < len(sample_names) else f'SAMPLE_{i}'] = dict(zip(format_keys, sample_values))
                        if 'GT' in format_keys and genotype is None:
                            gt_idx = format_keys.index('GT')
                            genotype = sample_values[gt_idx] if gt_idx < len(sample_values) else None

                variants.append({
                    'chrom': fields[0].replace('chr', '').replace('Chr', ''),
                    'pos': int(fields[1]),
                    'id': fields[2],
                    'ref': fields[3],
                    'alt': fields[4],
                    'qual': fields[5],
                    'filter': fields[6],
                    'info': fields[7],
                    'format': fields[8] if len(fields) > 8 else None,
                    'genotype': genotype,
                    'samples': sample_data,
                })

        return {
            'header': header_lines,
            'total': len(variants),
            'sample_count': len(sample_names),
            'sample_names': sample_names,
            'variants': variants,
        }
