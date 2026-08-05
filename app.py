#!/usr/bin/env python3
import argparse, json, sys
from pathlib import Path
from engine.vcf_parser import VCFParser
from engine.ann_parser import ANNParser
from engine.clinvar_parser import ClinVarParser
from engine.inheritance_engine import InheritanceEngine
from engine.evidence_engine import EvidenceEngine
from engine.risk_classifier import RiskClassifier
from engine.actionability_engine import ActionabilityEngine
from engine.phenotype_matcher import PhenotypeMatcher
from engine.medication_engine import MedicationEngine
from engine.report_engine import ReportEngine

def load_profile(path):
    if Path(path).exists():
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None

def analyze(v, engines, profile):
    result = {'chrom': v['chrom'], 'pos': v['pos'], 'ref': v['ref'], 'alt': v['alt'], 'id': v['id'], 'genotype': v.get('genotype')}

    ann = ANNParser.parse(v['info'])
    if ann:
        best = ANNParser.get_most_severe(ann)
        result.update({k: best.get(k) for k in ['gene_name','gene_id','effect','impact','hgvs_c','hgvs_p']})

    cv = ClinVarParser.parse(v['info'])
    if cv:
        result.update({k: cv.get(k) for k in ['significance','clinvar_significance_raw','disease','review_status','review_score']})
        result['clinvar_significance'] = cv.get('significance')

    gene = result.get('gene_name','')
    gt = result.get('genotype')
    clnsig = result.get('clinvar_significance','')

    inh = engines['inheritance'].assess(gene, gt, clnsig)
    result['inheritance_assessment'] = inh
    result['inheritance_adjustment'] = inh.get('score_adjustment',0)

    drug = engines['medication'].get_drug_guidance(gene)
    if drug: result['drug_guidance'] = drug

    score = EvidenceEngine.score(result)
    result.update({'score': score['total_score'], 'priority': score['priority'], 'evidence_factors': score['factors']})

    cat = RiskClassifier.classify(result)
    result.update(cat)

    act = engines['actionability'].assess(result)
    result['actionability'] = act

    if profile:
        personal = PhenotypeMatcher.match(result, profile)
        if personal:
            result['personal_context'] = personal
            result['score'] = max(0, result['score'] + personal.get('risk_modifier',0))

    result['summary'] = _summary(result)
    result['disease_description'] = _disease_desc(result.get('disease',''))
    result['recommendations'] = _recommendations(result)
    return result

def _summary(r):
    gene = r.get('gene_name','未知')
    sig = r.get('clinvar_significance','')
    inh = r.get('inheritance_assessment',{})
    if sig in ('pathogenic','likely_pathogenic') and inh.get('affected_status'):
        return f"{gene}基因的致病性变异，与{r.get('disease','相关疾病')}相关。"
    if sig == 'drug_response':
        return f"{gene}基因的药物反应变异，可能影响药物代谢。"
    if inh.get('carrier_status') and not inh.get('affected_status'):
        return f"{gene}基因携带者状态，通常不发病。"
    return f"{gene}基因的变异。"

def _disease_desc(d):
    dmap = {
        'Hereditary pancreatitis': '遗传性胰腺炎：导致胰腺反复发炎的遗传病。',
        'Recurrent pancreatitis': '复发性胰腺炎：胰腺反复发炎。',
        'Hereditary breast-ovarian cancer syndrome': '遗传性乳腺卵巢癌综合征：DNA修复基因变异导致癌症风险升高。',
        'Cystic fibrosis': '囊性纤维化：影响肺部和消化系统。',
        "Late-onset Alzheimer's disease": '晚发性阿尔茨海默病风险因素。',
        'Factor V Leiden thrombophilia': '凝血因子V Leiden血栓症：增加血栓风险。',
        'Hereditary hemochromatosis': '遗传性血色病：铁吸收过多。',
        'Sanfilippo syndrome type B': 'Sanfilippo综合征B型：罕见的遗传性代谢病。',
        'Nemaline myopathy': '线状体肌病：罕见的遗传性肌肉疾病。',
        'DPYD-related disorder': 'DPYD相关疾病：影响氟尿嘧啶类药物代谢。',
    }
    for k,v in dmap.items():
        if k.lower() in d.lower() or d.lower() in k.lower(): return v
    return ''

def _recommendations(r):
    recs = []
    act = r.get('actionability',{})
    recs.extend(act.get('actions',[]))
    inh = r.get('inheritance_assessment',{})
    if inh.get('carrier_status') and not inh.get('affected_status'):
        recs.append('生育前建议伴侣进行携带者筛查')
    if not recs:
        recs.append('建议与医疗提供者讨论')
    return recs

def main():
    parser = argparse.ArgumentParser(description='DNA Personal Genome Intelligence v0.4')
    parser.add_argument('vcf', help='VCF/VCF.GZ path')
    parser.add_argument('-o','--output', default='reports', help='Output dir')
    parser.add_argument('-p','--profile', default='user_profile/profile.json', help='User profile')
    parser.add_argument('--min-score', type=int, default=1)
    parser.add_argument('--max-variants', type=int, default=None)
    args = parser.parse_args()

    vcf_path = Path(args.vcf)
    if not vcf_path.exists():
        print(f'Error: file not found: {vcf_path}', file=sys.stderr)
        sys.exit(1)

    print('\n🧬 DNA Personal Genome Intelligence v0.4')
    print('=' * 50)

    engines = {
        'inheritance': InheritanceEngine('knowledge/inheritance.json'),
        'actionability': ActionabilityEngine('knowledge/diseases.json','knowledge/drugs.json'),
        'medication': MedicationEngine('knowledge/drugs.json'),
    }

    profile = load_profile(args.profile)
    if profile:
        print(f'👤 Profile loaded: {args.profile}')
    else:
        print('⚠️ No profile found. Run with --profile for personalized insights.')

    print(f'📁 Loading: {vcf_path}')
    data = VCFParser.parse(str(vcf_path))
    total = data['total']
    print(f'✅ Parsed {total:,} variants')

    variants = data['variants']
    if args.max_variants:
        variants = variants[:args.max_variants]
        print(f'🔬 Processing first {args.max_variants:,} variants...')
    else:
        print(f'🔬 Analyzing all variants...')

    findings = []
    for v in variants:
        analyzed = analyze(v, engines, profile)
        if analyzed['score'] >= args.min_score and analyzed.get('category') != 'research_vus':
            findings.append(analyzed)

    # Sort
    order = {'clinical_action':0, 'pharmacogenomics':1, 'disease_risk':2, 'carrier_status':3}
    findings.sort(key=lambda x: (order.get(x.get('category',''),99), -x['score']))

    print(f'\n📊 Results:')
    print(f'   Total: {total:,}')
    print(f'   Reported: {len(findings)}')

    cats = {}
    for f in findings:
        c = f.get('category_cn','其他')
        cats[c] = cats.get(c,0)+1
    for c,n in sorted(cats.items(), key=lambda x:-x[1]):
        print(f'   {c}: {n}')

    out = Path(args.output)
    out.mkdir(exist_ok=True)

    results = {'total': total, 'variants': findings}
    ReportEngine.generate_json(results, out/'report.json')
    ReportEngine.generate_html(results, out/'report.html')

    print(f'\n💾 reports/report.json')
    print(f'💾 reports/report.html')

    if findings:
        print(f'\n🔴 Top findings:')
        for f in findings[:5]:
            print(f"   {f.get('gene_name','?')} | {f.get('category_cn','')} | {f.get('significance','')} | Score:{f['score']}")

    print(f'\n✨ Done! Open {out}/report.html')

if __name__ == '__main__':
    main()
