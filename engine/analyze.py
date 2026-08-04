#!/usr/bin/env python3
"""
DNA Personal Genome Analyzer - Main Pipeline
Usage: python analyze.py <vcf_file> [--output reports/]
"""

import argparse
import gzip
import json
import sys
from pathlib import Path

from engine.variant_normalizer import VariantNormalizer
from engine.ann_parser import ANNParser
from engine.clinvar_parser import ClinVarParser
from engine.evidence_score import EvidenceScorer
from engine.interpretation import VariantInterpreter
from engine.report_generator import ReportGenerator


def parse_vcf(filepath):
    """Parse VCF or VCF.GZ file."""
    variants = []

    open_fn = gzip.open if str(filepath).endswith('.gz') else open

    with open_fn(filepath, 'rt') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue

            fields = line.split('\t')
            if len(fields) < 8:
                continue

            variants.append({
                'chrom': fields[0],
                'pos': int(fields[1]),
                'id': fields[2],
                'ref': fields[3],
                'alt': fields[4],
                'qual': fields[5],
                'filter': fields[6],
                'info': fields[7],
            })

    return variants


def analyze_variant(variant):
    """Run full analysis pipeline on a single variant."""
    result = {
        'chrom': variant['chrom'],
        'pos': variant['pos'],
        'ref': variant['ref'],
        'alt': variant['alt'],
        'id': variant['id'],
    }

    # 1. Parse ANN (SnpEff)
    ann_annotations = ANNParser.parse(variant['info'])
    if ann_annotations:
        best_ann = ANNParser.get_most_severe(ann_annotations)
        result.update({
            'gene_name': best_ann.get('gene_name'),
            'gene_id': best_ann.get('gene_id'),
            'feature_id': best_ann.get('feature_id'),
            'effect': best_ann.get('effect'),
            'impact': best_ann.get('impact'),
            'hgvs_c': best_ann.get('hgvs_c'),
            'hgvs_p': best_ann.get('hgvs_p'),
        })

    # 2. Parse ClinVar
    clinvar_data = ClinVarParser.parse(variant['info'])
    if clinvar_data:
        result.update({
            'clinvar_significance': clinvar_data.get('significance'),
            'clinvar_significance_raw': clinvar_data.get('significance_raw'),
            'disease': clinvar_data.get('disease'),
            'review_status': clinvar_data.get('review_status'),
            'allele_id': clinvar_data.get('allele_id'),
        })

    # 3. Score evidence
    score_data = EvidenceScorer.score_variant(result)
    result.update({
        'score': score_data['total_score'],
        'priority': score_data['priority'],
        'evidence_factors': score_data['factors'],
    })

    # 4. Generate interpretation
    interpretation = VariantInterpreter.interpret(result)
    result.update({
        'summary': interpretation['summary'],
        'recommendations': interpretation['recommendations'],
        'disease_description': interpretation['disease_description'],
    })

    return result


def filter_interesting(variants, min_score=5):
    """Filter variants worth reporting."""
    interesting = []
    for v in variants:
        analyzed = analyze_variant(v)
        if analyzed['score'] >= min_score:
            interesting.append(analyzed)

    # Sort by score descending
    interesting.sort(key=lambda x: x['score'], reverse=True)
    return interesting


def main():
    parser = argparse.ArgumentParser(description='DNA Personal Genome Analyzer')
    parser.add_argument('vcf', help='Path to VCF or VCF.GZ file')
    parser.add_argument('--output', '-o', default='reports', help='Output directory')
    parser.add_argument('--min-score', type=int, default=5, help='Minimum evidence score to report')
    parser.add_argument('--max-variants', type=int, default=None, help='Max variants to process (for testing)')
    args = parser.parse_args()

    vcf_path = Path(args.vcf)
    if not vcf_path.exists():
        print(f"Error: File not found: {vcf_path}", file=sys.stderr)
        sys.exit(1)

    print(f"📁 Loading: {vcf_path}")
    print(f"⏳ Parsing VCF...")

    variants = parse_vcf(vcf_path)
    total = len(variants)
    print(f"✅ Parsed {total:,} variants")

    if args.max_variants:
        variants = variants[:args.max_variants]
        print(f"🔬 Processing first {args.max_variants:,} variants...")
    else:
        print(f"🔬 Analyzing all variants...")

    interesting = filter_interesting(variants, min_score=args.min_score)

    print(f"\n📊 Results:")
    print(f"   Total variants: {total:,}")
    print(f"   Reported findings: {len(interesting)}")

    priorities = {}
    for v in interesting:
        p = v['priority']
        priorities[p] = priorities.get(p, 0) + 1

    for p, count in sorted(priorities.items(), key=lambda x: -x[1]):
        print(f"   {p}: {count}")

    # Generate reports
    output_dir = Path(args.output)
    output_dir.mkdir(exist_ok=True)

    results = {
        'total': total,
        'variants': interesting,
    }

    # JSON report
    json_path = output_dir / 'report.json'
    ReportGenerator.generate_json(results, json_path)
    print(f"\n💾 JSON report: {json_path}")

    # HTML report
    html_path = output_dir / 'report.html'
    ReportGenerator.generate_html(results, html_path)
    print(f"💾 HTML report: {html_path}")

    # Print top findings
    if interesting:
        print(f"\n🔴 Top findings:")
        for v in interesting[:5]:
            gene = v.get('gene_name', 'Unknown')
            sig = v.get('clinvar_significance', 'N/A')
            disease = v.get('disease', '')
            print(f"   {gene} | {sig} | {disease[:50] if disease else 'N/A'}")

    print(f"\n✨ Done! Open {html_path} in your browser.")


if __name__ == '__main__':
    main()
