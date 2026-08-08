#!/usr/bin/env python3
"""Inspect a DNA knowledge database before it is used for analysis.

This is intentionally a data-quality gate, not a clinical validation tool.
It reports whether the expected schema and clinically actionable ClinVar
records are present, so a partial import cannot silently look production ready.
"""
import argparse
import json
import sqlite3
import sys
from pathlib import Path


REQUIRED_TABLES = {
    "genes", "variants", "diseases", "variant_disease", "user_genotypes",
    "clinvar_snapshots", "variant_history", "user_alerts", "timeline_events",
    "family_members", "family_risks", "user_medications", "lab_results",
    "knowledge_sources", "gene_functions", "variant_traits", "ancestry_markers",
    "external_query_cache",
}
PATHOGENIC_LABELS = (
    "Pathogenic", "Likely_pathogenic", "Pathogenic/Likely_pathogenic",
)


def validate(db_path: Path) -> dict:
    if not db_path.exists():
        return {"ok": False, "error": f"Database does not exist: {db_path}"}

    with sqlite3.connect(db_path) as conn:
        tables = {
            row[0] for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        missing = sorted(REQUIRED_TABLES - tables)
        counts = {}
        for table in ("genes", "variants", "diseases", "variant_disease"):
            counts[table] = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        placeholders = ",".join("?" for _ in PATHOGENIC_LABELS)
        counts["pathogenic_or_likely_pathogenic"] = conn.execute(
            "SELECT COUNT(*) FROM variants "
            f"WHERE clinvar_significance IN ({placeholders})",
            PATHOGENIC_LABELS,
        ).fetchone()[0]

    warnings = []
    if not counts["variants"]:
        warnings.append("No variants are loaded; import a ClinVar release before analysis.")
    if counts["variants"] and not counts["pathogenic_or_likely_pathogenic"]:
        warnings.append("No pathogenic or likely pathogenic variants are present.")
    if missing:
        warnings.append("Missing required v3 tables: " + ", ".join(missing))

    return {
        "ok": not missing and counts["variants"] > 0,
        "database": str(db_path),
        "counts": counts,
        "missing_tables": missing,
        "warnings": warnings,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Validate a DNA knowledge database.")
    parser.add_argument(
        "database", nargs="?", type=Path,
        default=Path(__file__).parent.parent / "database" / "dna_knowledge.db",
    )
    args = parser.parse_args()
    result = validate(args.database)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(0 if result["ok"] else 1)
