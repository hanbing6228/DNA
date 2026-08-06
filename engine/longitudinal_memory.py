#!/usr/bin/env python3
"""
Longitudinal Genome Memory v3.0
Track variant evidence changes across ClinVar releases and auto-generate user alerts.
"""
import json
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path
import sys

BASE = Path(__file__).parent.parent
sys.path.insert(0, str(BASE))

from database.db import get_conn


class LongitudinalMemory:
    """Track user genotype evidence changes over time."""

    SIGNIFICANCE_RANK = {
        'Pathogenic': 5,
        'Likely_pathogenic': 4,
        'Uncertain_significance': 3,
        'Likely_benign': 2,
        'Benign': 1,
        'drug_response': 3,
    }

    @classmethod
    def record_snapshot(cls, record_count: int, version_tag: str = None) -> int:
        with get_conn() as conn:
            cur = conn.execute(
                "INSERT INTO clinvar_snapshots (record_count, version_tag) VALUES (?, ?)",
                (record_count, version_tag)
            )
            conn.commit()
            return cur.lastrowid

    @classmethod
    def track_variant_change(cls, variant_id: int, new_sig: str, new_rev: str,
                             snapshot_id: int, previous_sig: str = None):
        change_type = 'new'
        if previous_sig:
            old_rank = cls.SIGNIFICANCE_RANK.get(previous_sig, 0)
            new_rank = cls.SIGNIFICANCE_RANK.get(new_sig, 0)
            if new_rank > old_rank:
                change_type = 'upgraded'
            elif new_rank < old_rank:
                change_type = 'downgraded'
            else:
                change_type = 'unchanged'

        if change_type in ('upgraded', 'downgraded', 'new'):
            with get_conn() as conn:
                conn.execute(
                    """INSERT INTO variant_history
                    (variant_id, snapshot_id, clinvar_significance, clinvar_review_status,
                     change_type, previous_significance)
                    VALUES (?, ?, ?, ?, ?, ?)""",
                    (variant_id, snapshot_id, new_sig, new_rev, change_type, previous_sig)
                )
                conn.commit()
        return change_type

    @classmethod
    def check_user_impacts(cls, sample_name: str) -> List[Dict]:
        with get_conn() as conn:
            rows = conn.execute("""
                SELECT vh.*, v.chromosome, v.position, v.reference, v.alternate,
                       g.symbol as gene_symbol, ug.genotype
                FROM user_genotypes ug
                JOIN variants v ON ug.variant_id = v.id
                LEFT JOIN genes g ON v.gene_id = g.id
                JOIN variant_history vh ON v.id = vh.variant_id
                WHERE ug.sample_name = ? AND vh.change_type = 'upgraded'
                ORDER BY vh.changed_at DESC
            """, (sample_name,)).fetchall()
            return [dict(r) for r in rows]

    @classmethod
    def create_alert(cls, sample_name: str, variant_id: int, alert_type: str,
                     title: str, message: str, severity: str = 'warning'):
        with get_conn() as conn:
            conn.execute(
                """INSERT INTO user_alerts
                (sample_name, variant_id, alert_type, title, message, severity)
                VALUES (?, ?, ?, ?, ?, ?)""",
                (sample_name, variant_id, alert_type, title, message, severity)
            )
            conn.commit()

    @classmethod
    def get_alerts(cls, sample_name: str, unread_only: bool = False) -> List[Dict]:
        sql = "SELECT * FROM user_alerts WHERE sample_name = ?"
        params = [sample_name]
        if unread_only:
            sql += " AND is_read = 0"
        sql += " ORDER BY created_at DESC"
        with get_conn() as conn:
            rows = conn.execute(sql, params).fetchall()
            return [dict(r) for r in rows]

    @classmethod
    def mark_alert_read(cls, alert_id: int):
        with get_conn() as conn:
            conn.execute("UPDATE user_alerts SET is_read = 1 WHERE id = ?", (alert_id,))
            conn.commit()

    @classmethod
    def get_variant_timeline(cls, variant_id: int) -> List[Dict]:
        with get_conn() as conn:
            rows = conn.execute("""
                SELECT vh.*, cs.version_tag, cs.imported_at as snapshot_date
                FROM variant_history vh
                LEFT JOIN clinvar_snapshots cs ON vh.snapshot_id = cs.id
                WHERE vh.variant_id = ?
                ORDER BY vh.changed_at DESC
            """, (variant_id,)).fetchall()
            return [dict(r) for r in rows]


class GenomeMemoryEngine:
    """Auto-detect and notify users of knowledge-base updates affecting their genome."""

    @classmethod
    def process_clinvar_update(cls, sample_name: str, snapshot_id: int) -> int:
        impacts = LongitudinalMemory.check_user_impacts(sample_name)
        alert_count = 0
        for imp in impacts:
            gene = imp.get('gene_symbol', 'Unknown')
            prev = imp.get('previous_significance', 'Unknown')
            curr = imp.get('clinvar_significance', 'Unknown')
            title = f"{gene} Evidence Upgraded"
            message = (
                f"Your {gene} variant (Chr{imp['chromosome']}:{imp['position']}) "
                f"was upgraded from \"{prev}\" to \"{curr}\". "
                f"Please re-evaluate clinical significance."
            )
            LongitudinalMemory.create_alert(
                sample_name, imp['variant_id'], 'evidence_upgraded',
                title, message,
                'critical' if curr == 'Pathogenic' else 'warning'
            )
            alert_count += 1
        return alert_count

    @classmethod
    def check_medication_conflicts(cls, sample_name: str, new_medication: str) -> List[Dict]:
        conflicts = []
        with get_conn() as conn:
            rows = conn.execute("""
                SELECT v.id, v.chromosome, v.position, g.symbol as gene_symbol,
                       ug.genotype, ug.zygosity
                FROM user_genotypes ug
                JOIN variants v ON ug.variant_id = v.id
                LEFT JOIN genes g ON v.gene_id = g.id
                WHERE ug.sample_name = ?
            """, (sample_name,)).fetchall()

        for row in rows:
            gene = row['gene_symbol']
            if not gene:
                continue
            try:
                from web_api_v3 import get_drug_guidance
            except ImportError:
                from web_api_v2 import get_drug_guidance
            drug_info = get_drug_guidance(gene)
            if drug_info and drug_info.get('drugs'):
                for drug in drug_info['drugs']:
                    if new_medication.lower() in drug['drug'].lower():
                        conflicts.append({
                            'gene': gene,
                            'variant_id': row['id'],
                            'drug': drug['drug'],
                            'effect': drug['effect'],
                            'recommendation': drug['recommendation'],
                            'source': drug['source']
                        })
                        LongitudinalMemory.create_alert(
                            sample_name, row['id'], 'medication_conflict',
                            f"Medication Alert: {drug['drug']}",
                            f"Your {gene} variant may affect {drug['drug']}: {drug['effect']}. {drug['recommendation']}",
                            'critical'
                        )
        return conflicts
