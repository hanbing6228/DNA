#!/usr/bin/env python3
"""
Family Graph v3.0
Family pedigree, inheritance risk propagation, and genetic counseling support.
"""
import json
from typing import List, Dict, Optional
from pathlib import Path
import sys

BASE = Path(__file__).parent.parent
sys.path.insert(0, str(BASE))

from database.db import get_conn


class FamilyGraph:
    """Family genetic graph management."""

    @classmethod
    def add_member(cls, proband_sample: str, relation: str, name: str = None,
                   sex: str = None, affected: bool = False,
                   conditions: List[str] = None, has_genome: bool = False,
                   sample_name: str = None) -> int:
        with get_conn() as conn:
            cur = conn.execute(
                """INSERT INTO family_members
                (proband_sample, relation, name, sex, affected, conditions, has_genome, sample_name)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (proband_sample, relation, name, sex, int(affected),
                 json.dumps(conditions, ensure_ascii=False) if conditions else '[]',
                 int(has_genome), sample_name)
            )
            conn.commit()
            return cur.lastrowid

    @classmethod
    def get_family(cls, proband_sample: str) -> List[Dict]:
        with get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM family_members WHERE proband_sample = ? ORDER BY id",
                (proband_sample,)
            ).fetchall()
            results = []
            for r in rows:
                d = dict(r)
                d['conditions'] = json.loads(d.get('conditions', '[]'))
                results.append(d)
            return results

    @classmethod
    def calculate_family_risks(cls, proband_sample: str, findings: List[Dict]):
        family = cls.get_family(proband_sample)
        if not family:
            return []

        risks = []
        for f in findings:
            inh = f.get('inheritance', {})
            pattern = inh.get('pattern', '')
            gene = f.get('gene_symbol', 'Unknown')
            variant_id = f.get('variant_id')

            for member in family:
                relation = member['relation']
                risk_prob = 0.0
                risk_type = ''

                if pattern == 'AD':
                    if relation in ('father', 'mother', 'child'):
                        risk_prob = 0.5
                        risk_type = 'inherited'
                    elif relation == 'sibling':
                        risk_prob = 0.5 if member.get('affected') else 0.0
                        risk_type = 'inherited'

                elif pattern == 'AR':
                    if relation in ('father', 'mother'):
                        risk_prob = 0.0
                        risk_type = 'carrier_by_descent'
                    elif relation == 'sibling':
                        risk_prob = 0.25
                        risk_type = 'inherited'

                elif pattern == 'XL':
                    if relation == 'mother' and member.get('sex') == 'male':
                        risk_prob = 0.5
                        risk_type = 'inherited'
                    elif relation == 'mother' and member.get('sex') == 'female':
                        risk_prob = 0.5
                        risk_type = 'carrier_by_descent'

                if risk_prob > 0:
                    rec = cls._generate_recommendation(pattern, relation, risk_prob, gene)
                    risks.append({
                        'family_member_id': member['id'],
                        'relation': relation,
                        'gene_symbol': gene,
                        'risk_type': risk_type,
                        'probability': risk_prob,
                        'recommendation': rec
                    })
                    with get_conn() as conn:
                        conn.execute(
                            """INSERT OR REPLACE INTO family_risks
                            (proband_sample, family_member_id, gene_symbol, variant_id,
                             risk_type, probability, recommendation)
                            VALUES (?, ?, ?, ?, ?, ?, ?)""",
                            (proband_sample, member['id'], gene, variant_id,
                             risk_type, risk_prob, rec)
                        )
                        conn.commit()
        return risks

    @classmethod
    def _generate_recommendation(cls, pattern: str, relation: str, prob: float, gene: str) -> str:
        if pattern == 'AD' and prob >= 0.5:
            return f"{relation} has {prob*100:.0f}% chance of carrying the pathogenic {gene} variant. Genetic testing strongly recommended."
        elif pattern == 'AR' and relation in ('sibling',):
            return f"{relation} has {prob*100:.0f}% disease risk. Carrier screening recommended."
        elif pattern == 'XL' and relation == 'mother':
            return f"Mother has {prob*100:.0f}% chance of being a carrier. Confirmatory testing recommended."
        elif prob > 0:
            return f"{relation} has inherited risk. Consider genetic testing."
        return "Routine follow-up."

    @classmethod
    def get_pedigree_data(cls, proband_sample: str) -> Dict:
        family = cls.get_family(proband_sample)
        return {
            'proband': proband_sample,
            'members': family,
            'layout': cls._auto_layout(family)
        }

    @classmethod
    def _auto_layout(cls, family: List[Dict]) -> List[Dict]:
        positions = {
            'paternal_grandfather': {'x': 100, 'y': 50},
            'paternal_grandmother': {'x': 200, 'y': 50},
            'maternal_grandfather': {'x': 400, 'y': 50},
            'maternal_grandmother': {'x': 500, 'y': 50},
            'father': {'x': 150, 'y': 150},
            'mother': {'x': 450, 'y': 150},
            'proband': {'x': 300, 'y': 250},
            'sibling': {'x': 200, 'y': 250},
            'child': {'x': 300, 'y': 350},
        }
        layout = []
        for m in family:
            pos = positions.get(m['relation'], {'x': 300, 'y': 250})
            layout.append({
                'id': m['id'],
                'relation': m['relation'],
                'name': m.get('name', m['relation']),
                'x': pos['x'], 'y': pos['y'],
                'affected': bool(m.get('affected')),
                'sex': m.get('sex', 'unknown')
            })
        return layout

    @classmethod
    def get_family_risks(cls, proband_sample: str) -> List[Dict]:
        with get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM family_risks WHERE proband_sample = ? ORDER BY probability DESC",
                (proband_sample,)
            ).fetchall()
            return [dict(r) for r in rows]