#!/usr/bin/env python3
"""
Health Timeline v3.0
Unify all health data into a single chronological timeline.
"""
import json
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path
import sys

BASE = Path(__file__).parent.parent
sys.path.insert(0, str(BASE))

from database.db import get_conn


class HealthTimeline:
    """Unified health event timeline."""

    @classmethod
    def add_event(cls, sample_name: str, event_date: str, event_type: str,
                  source: str, title: str, description: str = None,
                  data: dict = None, variant_id: int = None):
        with get_conn() as conn:
            conn.execute(
                """INSERT INTO timeline_events
                (sample_name, event_date, event_type, source, title, description, data_json, related_variant_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (sample_name, event_date, event_type, source, title, description,
                 json.dumps(data, ensure_ascii=False) if data else None, variant_id)
            )
            conn.commit()

    @classmethod
    def get_timeline(cls, sample_name: str, event_types: List[str] = None,
                     start_date: str = None, end_date: str = None) -> List[Dict]:
        sql = "SELECT * FROM timeline_events WHERE sample_name = ?"
        params = [sample_name]
        if event_types:
            placeholders = ','.join('?' * len(event_types))
            sql += f" AND event_type IN ({placeholders})"
            params.extend(event_types)
        if start_date:
            sql += " AND event_date >= ?"
            params.append(start_date)
        if end_date:
            sql += " AND event_date <= ?"
            params.append(end_date)
        sql += " ORDER BY event_date DESC"
        with get_conn() as conn:
            rows = conn.execute(sql, params).fetchall()
            results = []
            for r in rows:
                d = dict(r)
                if d.get('data_json'):
                    d['data'] = json.loads(d['data_json'])
                    del d['data_json']
                results.append(d)
            return results

    @classmethod
    def auto_build_from_analysis(cls, sample_name: str, findings: List[Dict],
                                  profile: Dict = None, health_data: Dict = None,
                                  hospital_files: List[str] = None):
        """Auto-build timeline events from an analysis run."""
        today = datetime.now().strftime('%Y-%m-%d')

        # 1. Genome analysis event
        cls.add_event(
            sample_name, today, 'genome', 'vcf',
            'Genome Analysis Completed',
            f'Discovered {len(findings)} ClinVar-related variants',
            {'findings_count': len(findings),
             'categories': list(set(f.get('category_cn') for f in findings))}
        )

        # 2. Individual significant variants as events
        for f in findings:
            if f.get('category') in ('clinical_action', 'pharmacogenomics', 'disease_risk'):
                cls.add_event(
                    sample_name, today, 'genome', 'clinvar',
                    f"{f.get('gene_symbol', 'Unknown')} Variant Found",
                    f.get('description', ''),
                    {'significance': f.get('clinvar_significance'),
                     'score': f.get('score', {}).get('total_score')},
                    variant_id=f.get('variant_id')
                )

        # 3. Apple Health metrics
        if health_data and not health_data.get('error'):
            metrics = health_data.get('latest_metrics', {})
            for name, m in metrics.items():
                cls.add_event(
                    sample_name, m.get('date', today), 'wearable', 'apple_health',
                    f'Apple Health: {name}',
                    f'{name} = {m["value"]} {m.get("unit", "")}',
                    {'metric': name, 'value': m['value'], 'unit': m.get('unit')}
                )

        # 4. Hospital reports
        if hospital_files:
            for hf in hospital_files:
                cls.add_event(
                    sample_name, today, 'imaging', 'hospital_report',
                    f'Hospital Report: {hf}',
                    'User-uploaded medical lab/imaging report',
                    {'filename': hf}
                )

        # 5. Profile conditions (backdated)
        if profile:
            for cond in profile.get('conditions', []):
                cls.add_event(
                    sample_name, today, 'symptom', 'user_input',
                    f'Condition: {cond}',
                    'From personal health profile',
                    {'condition': cond}
                )
            for fh in profile.get('family_history', []):
                cls.add_event(
                    sample_name, today, 'milestone', 'user_input',
                    f'Family History: {fh.get("relation")} - {fh.get("condition")}',
                    'From personal health profile',
                    {'relation': fh.get('relation'), 'condition': fh.get('condition')}
                )

    @classmethod
    def get_risk_timeline(cls, sample_name: str, gene_symbol: str = None) -> List[Dict]:
        sql = """
            SELECT t.*, v.chromosome, v.position, g.symbol as gene_symbol
            FROM timeline_events t
            LEFT JOIN variants v ON t.related_variant_id = v.id
            LEFT JOIN genes g ON v.gene_id = g.id
            WHERE t.sample_name = ? AND t.event_type = 'genome'
        """
        params = [sample_name]
        if gene_symbol:
            sql += " AND g.symbol = ?"
            params.append(gene_symbol)
        sql += " ORDER BY t.event_date DESC"
        with get_conn() as conn:
            rows = conn.execute(sql, params).fetchall()
            return [dict(r) for r in rows]

    @classmethod
    def add_medication_event(cls, sample_name: str, drug_name: str,
                              start_date: str, dosage: str = None,
                              prescribed_by: str = None):
        cls.add_event(
            sample_name, start_date, 'medication', 'user_input',
            f'Started: {drug_name}',
            f'Dosage: {dosage}' if dosage else '',
            {'drug_name': drug_name, 'dosage': dosage, 'prescribed_by': prescribed_by}
        )

    @classmethod
    def add_lab_event(cls, sample_name: str, test_date: str, test_name: str,
                      value: float, unit: str, reference_range: str = None,
                      is_abnormal: bool = False):
        cls.add_event(
            sample_name, test_date, 'lab', 'hospital_report',
            f'Lab: {test_name}',
            f'{test_name} = {value} {unit}',
            {'test_name': test_name, 'value': value, 'unit': unit,
             'reference_range': reference_range, 'is_abnormal': is_abnormal}
        )
