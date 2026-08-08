#!/usr/bin/env python3
"""Import non-clinical genomic knowledge from reviewed, versioned exports.

Expected tab-separated columns:
  functions: gene_symbol,term_id,term_name,aspect,evidence_code,description
  ancestry: chromosome,position,reference,alternate,population_code,alternate_allele_frequency
  traits: chromosome,position,reference,alternate,trait_name,effect_allele,effect_size,
          effect_unit,p_value,population,evidence_level,limitations

Use official, versioned exports and provide their version, URL, and licence.
This script does not download or scrape data: source terms and licences differ,
and the operator must confirm the selected release is permitted for use.
"""
import argparse
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from database.db import (
    GeneRepository,
    GenomicContextRepository,
    KnowledgeSourceRepository,
    init_db,
)


def _source(args, category):
    return KnowledgeSourceRepository.upsert(
        args.source_key, args.source_name, category,
        version_tag=args.version, source_url=args.source_url, license=args.license,
    )


def _rows(path: Path, delimiter: str):
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter=delimiter)
        if not reader.fieldnames:
            raise ValueError("Input must contain a header row.")
        yield from reader


def import_functions(args):
    source_id = _source(args, "gene_function")
    count = 0
    for row in _rows(args.input, args.delimiter):
        for field in ("gene_symbol", "term_name"):
            if not row.get(field):
                raise ValueError(f"Missing {field} in function row {count + 2}.")
        gene_id = GeneRepository.upsert(row["gene_symbol"].strip())
        GenomicContextRepository.add_gene_function(
            gene_id, source_id, row["term_name"].strip(),
            term_id=row.get("term_id") or None,
            aspect=row.get("aspect") or None,
            evidence_code=row.get("evidence_code") or None,
            description=row.get("description") or None,
        )
        count += 1
    return count


def _location(row, line_number):
    required = ("chromosome", "position", "reference", "alternate")
    if any(not row.get(field) for field in required):
        raise ValueError(f"Missing genomic location in row {line_number}.")
    return {
        "chromosome": row["chromosome"].removeprefix("chr"),
        "position": int(row["position"]),
        "reference": row["reference"],
        "alternate": row["alternate"],
    }


def import_ancestry(args):
    source_id = _source(args, "ancestry_reference")
    count = 0
    for row in _rows(args.input, args.delimiter):
        record = _location(row, count + 2)
        if not row.get("population_code"):
            raise ValueError(f"Missing population_code in row {count + 2}.")
        frequency = float(row["alternate_allele_frequency"])
        if not 0 <= frequency <= 1:
            raise ValueError(f"alternate_allele_frequency must be in [0, 1] at row {count + 2}.")
        GenomicContextRepository.add_ancestry_marker({
            **record,
            "population_code": row["population_code"],
            "alternate_allele_frequency": frequency,
            "source_id": source_id,
        })
        count += 1
    return count


def import_traits(args):
    source_id = _source(args, "research_trait")
    count = 0
    for row in _rows(args.input, args.delimiter):
        record = _location(row, count + 2)
        if not row.get("trait_name"):
            raise ValueError(f"Missing trait_name in row {count + 2}.")
        GenomicContextRepository.add_trait_association({
            **record,
            "rsid": row.get("rsid") or None,
            "trait_name": row["trait_name"],
            "trait_category": row.get("trait_category") or None,
            "effect_allele": row.get("effect_allele") or None,
            "effect_size": float(row["effect_size"]) if row.get("effect_size") else None,
            "effect_unit": row.get("effect_unit") or None,
            "p_value": float(row["p_value"]) if row.get("p_value") else None,
            "population": row.get("population") or None,
            "evidence_level": row.get("evidence_level") or "research",
            "limitations": row.get("limitations") or None,
            "source_id": source_id,
        })
        count += 1
    return count


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Import versioned genomic context data.")
    parser.add_argument("kind", choices=("functions", "ancestry", "traits"))
    parser.add_argument("input", type=Path)
    parser.add_argument("--source-key", required=True)
    parser.add_argument("--source-name", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--source-url", required=True)
    parser.add_argument("--license", required=True)
    parser.add_argument("--delimiter", default="\t")
    args = parser.parse_args()
    init_db()
    imported = {"functions": import_functions, "ancestry": import_ancestry, "traits": import_traits}[args.kind](args)
    print(f"Imported {imported} {args.kind} records from {args.source_name} {args.version}.")
