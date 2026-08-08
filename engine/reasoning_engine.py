#!/usr/bin/env python3
import sys
from pathlib import Path
from typing import Dict, List, Optional

sys.path.insert(0, str(Path(__file__).parent.parent))


class InheritanceRule:
    PATTERNS = {
        'AD': {'name': 'Autosomal Dominant', 'affected_heterozygous': True, 'affected_homozygous': True},
        'AR': {'name': 'Autosomal Recessive', 'affected_heterozygous': False, 'affected_homozygous': True},
        'XL': {'name': 'X-linked', 'affected_hemizygous': True, 'affected_heterozygous': False},
    }

    @classmethod
    def assess(cls, inheritance: str, zygosity: str, significance: str) -> Dict:
        result = {
            'pattern': inheritance or 'Unknown',
            'pattern_name': cls.PATTERNS.get(inheritance, {}).get('name', 'Unknown'),
            'zygosity': zygosity or 'unknown',
            'affected_status': False,
            'carrier_status': False,
            'penetrance': 1.0,
            'confidence': 'low',
            'explanation': ''
        }

        if significance not in ('Pathogenic', 'Likely_pathogenic', 'Pathogenic/Likely_pathogenic'):
            result['explanation'] = 'Variant not classified as pathogenic.'
            return result

        if inheritance == 'AD':
            if zygosity in ('heterozygous', 'homozygous'):
                result['affected_status'] = True
                result['penetrance'] = 0.8
                result['confidence'] = 'medium'
                result['explanation'] = 'Autosomal dominant: one pathogenic allele is sufficient to cause disease. Penetrance ~80%.'
        elif inheritance == 'AR':
            if zygosity == 'homozygous':
                result['affected_status'] = True
                result['confidence'] = 'high'
                result['explanation'] = 'Autosomal recessive: homozygous pathogenic variant - disease likely present.'
            elif zygosity == 'heterozygous':
                result['carrier_status'] = True
                result['confidence'] = 'high'
                result['explanation'] = 'Autosomal recessive: heterozygous carrier - typically asymptomatic.'
        elif inheritance == 'XL':
            if zygosity == 'hemizygous':
                result['affected_status'] = True
                result['confidence'] = 'high'
                result['explanation'] = 'X-linked: hemizygous male - disease likely present.'
            elif zygosity == 'heterozygous':
                result['carrier_status'] = True
                result['confidence'] = 'medium'
                result['explanation'] = 'X-linked: female carrier - may have mild symptoms or be asymptomatic.'
        else:
            if zygosity in ('heterozygous', 'homozygous', 'hemizygous'):
                result['affected_status'] = True
                result['confidence'] = 'low'
                result['explanation'] = 'Inheritance pattern unknown - cannot determine risk from zygosity alone.'

        return result


class EvidenceScorer:
    REVIEW_WEIGHTS = {
        'practice guideline': 4,
        'reviewed by expert panel': 3,
        'criteria provided multiple submitters no conflicts': 2,
        'criteria provided single submitter': 1,
        'criteria provided conflicting interpretations': 0,
        'no assertion criteria provided': -1,
        'no assertion provided': -2,
    }

    SIGNIFICANCE_SCORES = {
        'Pathogenic': 10,
        'Likely_pathogenic': 7,
        'Pathogenic/Likely_pathogenic': 8,
        'Uncertain_significance': 2,
        'Likely_benign': -2,
        'Benign': -5,
        'drug_response': 5,
    }

    @classmethod
    def score(cls, variant: Dict, inheritance_result: Dict) -> Dict:
        sig = variant.get('clinvar_significance', '')
        revstat = variant.get('clinvar_review_status', '') or ''

        sig_score = cls.SIGNIFICANCE_SCORES.get(sig, 0)
        rev_score = 0
        for key, weight in cls.REVIEW_WEIGHTS.items():
            if key in revstat.lower():
                rev_score = weight
                break

        inh = inheritance_result
        inh_bonus = 0
        if inh['affected_status'] and inh['confidence'] == 'high':
            inh_bonus = 3
        elif inh['carrier_status']:
            inh_bonus = 1

        total = sig_score + rev_score + inh_bonus

        return {
            'total_score': max(0, total),
            'significance_score': sig_score,
            'review_score': rev_score,
            'inheritance_bonus': inh_bonus,
            'priority': 'high' if total >= 10 else 'medium' if total >= 5 else 'low',
            'factors': {
                'clinvar_significance': sig,
                'review_status': revstat,
                'inheritance_pattern': inh['pattern'],
                'affected_status': inh['affected_status'],
                'carrier_status': inh['carrier_status'],
            }
        }


class RiskClassifier:
    @classmethod
    def classify(cls, variant: Dict, score: Dict, inheritance: Dict) -> Dict:
        sig = variant.get('clinvar_significance', '')

        if sig == 'drug_response':
            return {
                'category': 'pharmacogenomics',
                'category_cn': '药物基因组学',
                'icon': '💊',
                'urgency': 'medium',
                'description': '该变异可能影响药物代谢或反应，用药前建议咨询医生。'
            }

        if inheritance.get('affected_status') and score['total_score'] >= 7:
            return {
                'category': 'clinical_action',
                'category_cn': '需要临床行动',
                'icon': '🔴',
                'urgency': 'high',
                'description': f'致病性变异，{inheritance["pattern_name"]}遗传模式，建议尽快就医咨询。'
            }

        if inheritance.get('carrier_status'):
            return {
                'category': 'carrier_status',
                'category_cn': '携带者状态',
                'icon': '🟡',
                'urgency': 'low',
                'description': '携带者状态，通常不发病，但生育前建议伴侣筛查。'
            }

        if score['total_score'] >= 5:
            return {
                'category': 'disease_risk',
                'category_cn': '疾病风险',
                'icon': '🟠',
                'urgency': 'medium',
                'description': '风险因素或复杂遗传关联，建议结合临床表现评估。'
            }

        return {
            'category': 'research_vus',
            'category_cn': '研究意义不明',
            'icon': '⚪',
            'urgency': 'none',
            'description': '证据不足，暂无临床意义。'
        }


class ActionabilityEngine:
    @classmethod
    def assess(cls, category: str, gene_symbol: str, disease_name: str) -> Dict:
        actions = []

        if category == 'clinical_action':
            actions.extend([
                '尽快预约遗传咨询专科',
                '告知直系亲属，建议家族筛查',
                '建立专科随访档案',
            ])
            if 'cancer' in (disease_name or '').lower() or 'tumor' in (disease_name or '').lower():
                actions.append('根据指南启动早期筛查方案')
            if 'pancreatitis' in (disease_name or '').lower():
                actions.extend(['严格禁酒', '避免高脂饮食', '定期检测淀粉酶/脂肪酶'])

        elif category == 'pharmacogenomics':
            actions.extend([
                '携带此报告就诊时主动告知医生',
                '开始新药物前查询药物基因组指南',
                '避免自行调整药物剂量',
            ])

        elif category == 'carrier_status':
            actions.extend([
                '伴侣如有生育计划，建议进行携带者筛查',
                '了解该疾病的产前诊断选项',
                '保持常规健康体检',
            ])

        elif category == 'disease_risk':
            actions.extend([
                '结合个人和家族病史综合评估',
                '保持定期体检',
                '关注相关症状的早期表现',
            ])

        return {
            'actions': actions,
            'follow_up': '建议6-12个月复查医学知识库更新',
            'genetic_counseling_recommended': category in ('clinical_action', 'carrier_status'),
        }


class ReasoningEngine:
    @classmethod
    def analyze(cls, variant: Dict, genotype: str, user_profile: Optional[Dict] = None) -> Dict:
        gene_symbol = variant.get('gene_symbol') or variant.get('gene_name', '未知')
        significance = variant.get('clinvar_significance', '')

        inheritance = variant.get('inheritance_pattern', '')
        if not inheritance and gene_symbol != '未知':
            inheritance = cls._infer_inheritance(gene_symbol)

        zygosity = cls._genotype_to_zygosity(genotype)

        inh_result = InheritanceRule.assess(inheritance, zygosity, significance)
        score = EvidenceScorer.score(variant, inh_result)
        risk = RiskClassifier.classify(variant, score, inh_result)
        action = ActionabilityEngine.assess(risk['category'], gene_symbol, variant.get('disease', ''))

        personal = None
        if user_profile:
            personal = cls._match_phenotype(variant, user_profile)

        finding = {
            'variant_id': variant.get('id'),
            'chrom': variant.get('chromosome'),
            'pos': variant.get('position'),
            'ref': variant.get('reference'),
            'alt': variant.get('alternate'),
            'gene_symbol': gene_symbol,
            'genotype': genotype,
            'zygosity': zygosity,
            'clinvar_significance': significance,
            'disease': variant.get('disease', ''),
            'inheritance': inh_result,
            'score': score,
            'category': risk['category'],
            'category_cn': risk['category_cn'],
            'icon': risk['icon'],
            'urgency': risk['urgency'],
            'description': risk['description'],
            'actionability': action,
            'personal_context': personal,
            'recommendations': action['actions'],
        }

        return finding

    @staticmethod
    def _genotype_to_zygosity(gt: str) -> str:
        # VCF genotype fields can include FORMAT subfields (for example
        # "0/1:42:99").  Only the GT component determines zygosity.
        gt = (gt or '').split(':', 1)[0]
        if gt in ('0/1', '0|1', '1/0', '1|0'):
            return 'heterozygous'
        if gt in ('1/1', '1|1'):
            return 'homozygous'
        if gt in ('1', './1', '.|1'):
            return 'hemizygous'
        return 'unknown'

    @staticmethod
    def _infer_inheritance(gene_symbol: str) -> str:
        ad_genes = {'PRSS1', 'BRCA1', 'BRCA2', 'APOE', 'CFTR', 'F5'}
        ar_genes = {'NAGLU', 'DPYD', 'MTHFR'}
        if gene_symbol in ad_genes:
            return 'AD'
        if gene_symbol in ar_genes:
            return 'AR'
        return ''

    @staticmethod
    def _match_phenotype(variant: Dict, profile: Dict) -> Optional[Dict]:
        conditions = profile.get('conditions', [])
        family = profile.get('family_history', [])

        modifier = 0
        matched = []
        disease = (variant.get('disease') or '').lower()

        for cond in conditions:
            if cond.lower() in disease or any(word in disease for word in cond.lower().split()):
                modifier += 2
                matched.append(f'个人病史: {cond}')

        for fh in family:
            relation = fh.get('relation', '')
            cond = fh.get('condition', '')
            if cond.lower() in disease or any(word in disease for word in cond.lower().split()):
                modifier += 1
                matched.append(f'家族史: {relation}有{cond}')

        if matched:
            return {
                'risk_modifier': modifier,
                'matched_factors': matched,
                'assessment': '个人/家族病史与基因关联疾病有重叠，建议重点关注。'
            }
        return None
