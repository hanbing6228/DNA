#!/usr/bin/env python3
"""
ClinVar VCF -> SQLite Knowledge Graph Importer v2.1
Usage: python import_clinvar.py <clinvar.vcf.gz> [max_records]
       python import_clinvar.py <clinvar.vcf.gz> all    # import all
"""
import gzip
import sys
import re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from database.db import init_db, GeneRepository, DiseaseRepository, VariantRepository, VariantDiseaseRepository


def parse_geneinfo(info: str) -> list:
    match = re.search(r'GENEINFO=([^;]+)', info)
    if not match:
        return []
    genes = []
    for part in match.group(1).split('|'):
        if ':' in part:
            symbol, gid = part.split(':', 1)
            genes.append((symbol.strip(), gid.strip()))
    return genes


def parse_clnsig(info: str) -> str:
    match = re.search(r'CLNSIG=([^;]+)', info)
    return match.group(1) if match else None


def parse_clnrevstat(info: str) -> str:
    match = re.search(r'CLNREVSTAT=([^;]+)', info)
    return match.group(1).replace('_', ' ') if match else None


def parse_clndn(info: str) -> list:
    match = re.search(r'CLNDN=([^;]+)', info)
    if not match:
        return []
    raw = match.group(1)
    diseases = []
    for d in raw.split('|'):
        d = d.strip()
        if d and d != 'not_provided':
            d = d.replace('\\\\', '').replace('_', ' ')
            diseases.append(d)
    return diseases


def parse_rs(info: str) -> str:
    match = re.search(r'RS=([^;]+)', info)
    return match.group(1) if match else None


def parse_variation_id(info: str) -> str:
    match = re.search(r'CLNVCID=([^;]+)', info)
    if not match:
        match = re.search(r'CLNVI=([^;]+)', info)
    return match.group(1) if match else None


def parse_hgvs(info: str) -> dict:
    result = {}
    m = re.search(r'CLNHGVS=([^;]+)', info)
    if m:
        result['genomic'] = m.group(1)
    return result


def import_clinvar(vcf_path: str, max_records: int = None):
    init_db()
    open_fn = gzip.open if vcf_path.endswith('.gz') else open
    imported = 0
    skipped = 0

    print(f"Importing {vcf_path}...")
    print("This may take a few minutes for large files. Press Ctrl+C to stop.\n")

    with open_fn(vcf_path, 'rt', encoding='utf-8', errors='ignore') as f:
        for line in f:
            if line.startswith('#'):
                continue
            fields = line.strip().split('\t')
            if len(fields) < 8:
                continue

            chrom = fields[0].replace('chr', '').replace('Chr', '')
            pos = int(fields[1])
            ref = fields[3]
            alt = fields[4]
            info = fields[7]

            gene_symbols = parse_geneinfo(info)
            gene_id = None
            if gene_symbols:
                sym, ensembl = gene_symbols[0]
                gene_id = GeneRepository.upsert(symbol=sym, ensembl_id=ensembl)

            sig = parse_clnsig(info)
            revstat = parse_clnrevstat(info)
            rs = parse_rs(info)
            var_id = parse_variation_id(info)
            hgvs = parse_hgvs(info)

            if not sig:
                skipped += 1
                continue

            variant_db_id = VariantRepository.upsert(
                chrom=chrom, pos=pos, ref=ref, alt=alt,
                gene_id=gene_id,
                hgvs_genomic=hgvs.get('genomic'),
                clinvar_significance=sig,
                clinvar_review_status=revstat,
                dbsnp_id=rs,
                clinvar_variation_id=var_id,
                raw_info=info[:2000]
            )

            diseases = parse_clndn(info)
            for dname in diseases:
                if not dname or dname.lower() in ('not specified', 'see cases', 'not provided'):
                    continue
                did = DiseaseRepository.upsert(name=dname)
                VariantDiseaseRepository.link(
                    variant_db_id, did,
                    significance=sig,
                    evidence_level=revstat
                )

            imported += 1
            if imported % 10000 == 0:
                print(f"  Imported {imported:,} variants... (skipped {skipped:,})")

            if max_records and imported >= max_records:
                break

    print(f"\n✅ Done. Imported {imported:,} variants. Skipped {skipped:,} (no significance).")
    print(f"Database location: {Path(__file__).parent.parent / 'database' / 'dna_knowledge.db'}")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python import_clinvar.py <clinvar.vcf.gz> [max_records | all]")
        print("Examples:")
        print("  python import_clinvar.py data/clinvar.vcf.gz          # import all")
        print("  python import_clinvar.py data/clinvar.vcf.gz 5000   # import first 5000")
        sys.exit(1)

    vcf = sys.argv[1]
    limit = None
    if len(sys.argv) > 2:
        if sys.argv[2].lower() == 'all':
            limit = None
        else:
            limit = int(sys.argv[2])

    import_clinvar(vcf, limit)
