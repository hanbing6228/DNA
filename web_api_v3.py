#!/usr/bin/env python3
"""
DNA Personal Genome Intelligence v3.0
- Knowledge Graph + Reasoning Engine
- Longitudinal Genome Memory
- Health Timeline
- Family Graph
- Apple Health XML parsing
- Enhanced drug database (CPIC/PharmGKB)
"""
import json, sys, gzip, re, xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename

BASE = Path(__file__).parent
sys.path.insert(0, str(BASE))

from database.db import init_db, UserGenotypeRepository, get_conn
from engine.knowledge_service import KnowledgeService
from engine.reasoning_engine import ReasoningEngine
from engine.longitudinal_memory import LongitudinalMemory, GenomeMemoryEngine
from engine.health_timeline import HealthTimeline
from engine.family_graph import FamilyGraph

app = Flask(__name__, template_folder=str(BASE / "templates"))
UPLOAD = BASE / "uploads"
REPORT = BASE / "reports"
UPLOAD.mkdir(exist_ok=True)
REPORT.mkdir(exist_ok=True)
app.config["MAX_CONTENT_LENGTH"] = 500 * 1024 * 1024

init_db()

# ============================================================
# v3.0: Apply schema_v3 additions
# ============================================================
def _apply_v3_schema():
    schema_v3 = BASE / "database" / "schema_v3.sql"
    if schema_v3.exists():
        import sqlite3
        db_path = BASE / "database" / "dna_knowledge.db"
        conn = sqlite3.connect(db_path)
        conn.executescript(schema_v3.read_text())
        conn.close()

_apply_v3_schema()

# ============================================================
# Drug Database (CPIC / PharmGKB)
# ============================================================
DRUG_DB = {
    'MTHFR': {
        'drugs': [
            {'drug': 'Methotrexate', 'effect': 'Toxicity risk increased', 'recommendation': 'Consider dose reduction or monitor blood levels', 'source': 'CPIC'},
            {'drug': '5-Fluorouracil (5-FU)', 'effect': 'Increased toxicity', 'recommendation': 'Use with caution, close monitoring', 'source': 'CPIC'},
            {'drug': 'Folic acid supplements', 'effect': 'May need supplementation', 'recommendation': 'Consult doctor about active folate', 'source': 'PharmGKB'},
        ],
        'description': 'MTHFR encodes methylenetetrahydrofolate reductase, affecting folate metabolism and drug response.'
    },
    'DPYD': {
        'drugs': [
            {'drug': '5-Fluorouracil (5-FU)', 'effect': 'Severe toxicity risk', 'recommendation': 'Contraindicated or major dose reduction, genetic testing required', 'source': 'CPIC'},
            {'drug': 'Capecitabine', 'effect': 'Severe toxicity risk', 'recommendation': 'Contraindicated or major dose reduction', 'source': 'CPIC'},
            {'drug': 'Tegafur', 'effect': 'Toxicity risk increased', 'recommendation': 'Avoid use', 'source': 'CPIC'},
        ],
        'description': 'DPYD encodes dihydropyrimidine dehydrogenase, the key enzyme for fluoropyrimidine metabolism.'
    },
    'CYP2D6': {
        'drugs': [
            {'drug': 'Codeine', 'effect': 'May be ineffective or ultra-rapid metabolized', 'recommendation': 'Avoid, switch to alternative analgesic', 'source': 'CPIC'},
            {'drug': 'Tamoxifen', 'effect': 'Efficacy may be reduced', 'recommendation': 'Consider alternative endocrine therapy', 'source': 'CPIC'},
            {'drug': 'Tramadol', 'effect': 'Metabolism variation', 'recommendation': 'Monitor efficacy, adjust if needed', 'source': 'PharmGKB'},
        ],
        'description': 'CYP2D6 is a major drug-metabolizing enzyme affecting plasma concentrations of many drugs.'
    },
    'CYP2C19': {
        'drugs': [
            {'drug': 'Clopidogrel (Plavix)', 'effect': 'Antiplatelet effect may be insufficient', 'recommendation': 'Consider switching to ticagrelor or prasugrel', 'source': 'CPIC'},
            {'drug': 'Omeprazole', 'effect': 'Efficacy may be enhanced', 'recommendation': 'Standard dose usually safe', 'source': 'PharmGKB'},
            {'drug': 'Diazepam', 'effect': 'Slower metabolism', 'recommendation': 'Consider dose reduction', 'source': 'PharmGKB'},
        ],
        'description': 'CYP2C19 affects clopidogrel metabolism and is closely related to cardiovascular therapy.'
    },
    'CYP2C9': {
        'drugs': [
            {'drug': 'Warfarin', 'effect': 'Bleeding risk increased', 'recommendation': 'Reduce starting dose, closely monitor INR', 'source': 'CPIC'},
            {'drug': 'Phenytoin', 'effect': 'Toxicity risk', 'recommendation': 'Halve starting dose', 'source': 'CPIC'},
            {'drug': 'Celecoxib', 'effect': 'Increased exposure', 'recommendation': 'Lowest effective dose', 'source': 'PharmGKB'},
        ],
        'description': 'CYP2C9 participates in warfarin metabolism; variants significantly affect anticoagulation therapy.'
    },
    'VKORC1': {
        'drugs': [
            {'drug': 'Warfarin', 'effect': 'Increased warfarin sensitivity', 'recommendation': 'Significantly reduce starting dose', 'source': 'CPIC'},
        ],
        'description': 'VKORC1 is the warfarin target; variants affect anticoagulation sensitivity.'
    },
    'SLCO1B1': {
        'drugs': [
            {'drug': 'Simvastatin', 'effect': 'Myopathy risk increased', 'recommendation': 'Consider low dose or switch statin', 'source': 'CPIC'},
            {'drug': 'Atorvastatin', 'effect': 'Mild risk increase', 'recommendation': 'Monitor creatine kinase', 'source': 'PharmGKB'},
        ],
        'description': 'SLCO1B1 affects hepatic uptake of statins and is associated with myopathy risk.'
    },
    'TPMT': {
        'drugs': [
            {'drug': 'Azathioprine', 'effect': 'Severe myelosuppression risk', 'recommendation': 'Major dose reduction or avoid', 'source': 'CPIC'},
            {'drug': '6-Mercaptopurine', 'effect': 'Severe myelosuppression risk', 'recommendation': 'Major dose reduction', 'source': 'CPIC'},
            {'drug': 'Thioguanine', 'effect': 'Toxicity risk', 'recommendation': 'Major dose reduction', 'source': 'CPIC'},
        ],
        'description': 'TPMT deficiency causes severe thiopurine toxicity; testing required before use.'
    },
    'HLA-B': {
        'drugs': [
            {'drug': 'Carbamazepine', 'effect': 'Stevens-Johnson syndrome risk', 'recommendation': 'Contraindicated if HLA-B*15:02 positive', 'source': 'CPIC'},
            {'drug': 'Allopurinol', 'effect': 'Severe skin reaction risk', 'recommendation': 'Use with caution if HLA-B*58:01 positive', 'source': 'CPIC'},
        ],
        'description': 'HLA-B alleles are associated with severe cutaneous adverse drug reactions.'
    },
    'CFTR': {
        'drugs': [
            {'drug': 'Ivacaftor', 'effect': 'Effective for specific mutations', 'recommendation': 'Confirm specific mutation type', 'source': 'FDA'},
        ],
        'description': 'CFTR mutations affect response to cystic fibrosis therapeutics.'
    },
    'PRSS1': {
        'drugs': [
            {'drug': 'Alcohol', 'effect': 'Triggers acute pancreatitis attacks', 'recommendation': 'Strict abstinence from alcohol', 'source': 'Clinical Guideline'},
        ],
        'description': 'PRSS1 pathogenic variants cause hereditary pancreatitis; lifestyle modification critical.'
    },
}


def get_drug_guidance(gene_symbol: str) -> dict:
    return DRUG_DB.get(gene_symbol.upper(), None)


# ============================================================
# Apple Health XML Parser
# ============================================================
def parse_apple_health(xml_path: Path) -> dict:
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        records = []
        for record in root.findall('.//Record'):
            rtype = record.get('type', '')
            value = record.get('value', '')
            unit = record.get('unit', '')
            date = record.get('startDate', '')[:10]
            if rtype and value:
                try:
                    float(value)
                    records.append({'type': rtype, 'value': float(value), 'unit': unit, 'date': date})
                except ValueError:
                    pass

        key_types = {
            'HKQuantityTypeIdentifierHeartRate': 'Resting Heart Rate',
            'HKQuantityTypeIdentifierBloodPressureSystolic': 'Systolic BP',
            'HKQuantityTypeIdentifierBloodPressureDiastolic': 'Diastolic BP',
            'HKQuantityTypeIdentifierBloodGlucose': 'Blood Glucose',
            'HKQuantityTypeIdentifierBodyMassIndex': 'BMI',
            'HKQuantityTypeIdentifierBodyFatPercentage': 'Body Fat %',
            'HKQuantityTypeIdentifierOxygenSaturation': 'SpO2',
            'HKQuantityTypeIdentifierStepCount': 'Steps',
            'HKQuantityTypeIdentifierDistanceWalkingRunning': 'Walking Distance',
            'HKQuantityTypeIdentifierActiveEnergyBurned': 'Active Energy',
            'HKQuantityTypeIdentifierBasalEnergyBurned': 'Basal Metabolic Rate',
            'HKQuantityTypeIdentifierSleepAnalysis': 'Sleep',
        }

        latest = {}
        for r in records:
            short = r['type'].replace('HKQuantityTypeIdentifier', '').replace('HKCategoryTypeIdentifier', '')
            name = key_types.get(r['type'], short)
            if name not in latest or (r['date'] and r['date'] > latest[name]['date']):
                latest[name] = r

        trends = {}
        for name, r in latest.items():
            trends[name] = {'value': r['value'], 'unit': r['unit'], 'date': r['date']}

        return {
            'record_count': len(records),
            'latest_metrics': trends,
            'summary': f"Parsed {len(records)} health records, extracted {len(trends)} key metrics."
        }
    except Exception as e:
        return {'error': str(e), 'record_count': 0}


# ============================================================
# VCF Parser
# ============================================================
def parse_vcf(vcf_path: str, max_variants: int = None):
    open_fn = gzip.open if vcf_path.endswith('.gz') else open
    variants = []
    with open_fn(vcf_path, 'rt', encoding='utf-8', errors='ignore') as f:
        for line in f:
            if line.startswith('#'):
                continue
            fields = line.strip().split('\t')
            if len(fields) < 8:
                continue
            gt = None
            if len(fields) > 9:
                fmt = fields[8].split(':')
                if 'GT' in fmt:
                    vals = fields[9].split(':')
                    gt_idx = fmt.index('GT')
                    if gt_idx < len(vals):
                        gt = vals[gt_idx]
            variants.append({
                'chrom': fields[0].replace('chr', '').replace('Chr', ''),
                'pos': int(fields[1]),
                'ref': fields[3],
                'alt': fields[4],
                'id': fields[2],
                'info': fields[7],
                'genotype': gt,
            })
            if max_variants and len(variants) >= max_variants:
                break
    return variants


# ============================================================
# Routes
# ============================================================
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/analyze", methods=["POST"])
def analyze_api():
    vcf = request.files.get("vcf")
    if not vcf or vcf.filename == "":
        return jsonify({"error": "Please upload a VCF file"}), 400

    vcf_path = UPLOAD / secure_filename(vcf.filename)
    vcf.save(vcf_path)

    # Parse profile
    profile = None
    if request.files.get("profile"):
        p = UPLOAD / secure_filename(request.files["profile"].filename)
        request.files["profile"].save(p)
        try:
            profile = json.load(open(p, encoding='utf-8'))
        except Exception:
            pass
    elif request.form.get("profile_json"):
        try:
            profile = json.loads(request.form["profile_json"])
        except Exception:
            pass

    # Parse Apple Health
    health_data = None
    if request.files.get("health"):
        h = UPLOAD / secure_filename(request.files["health"].filename)
        request.files["health"].save(h)
        health_data = parse_apple_health(h)

    # Save hospital reports
    hospital_files = []
    reports = request.files.getlist("reports")
    if reports and reports[0].filename:
        hdir = UPLOAD / "hospital"
        hdir.mkdir(exist_ok=True)
        for f in reports:
            if f.filename:
                fp = hdir / secure_filename(f.filename)
                f.save(fp)
                hospital_files.append(f.filename)

    max_v = request.form.get("max_variants", type=int) or 50000
    min_s = request.form.get("min_score", 0, type=int)

    raw_variants = parse_vcf(str(vcf_path), max_v)
    total = len(raw_variants)
    findings = []
    sample_name = secure_filename(vcf.filename).split('.')[0]

    for v in raw_variants:
        kg_variant = KnowledgeService.get_variant(v['chrom'], v['pos'], v['ref'], v['alt'])
        if not kg_variant:
            continue

        finding = ReasoningEngine.analyze(kg_variant, v['genotype'], profile)

        gene = finding.get('gene_symbol', '')
        if gene:
            drug_info = get_drug_guidance(gene)
            if drug_info:
                finding['drug_database'] = drug_info
                if 'drug_guidance' not in finding or not finding['drug_guidance']:
                    finding['drug_guidance'] = drug_info

        if finding['score']['total_score'] >= min_s and finding['category'] != 'research_vus':
            findings.append(finding)
            if kg_variant.get('id'):
                UserGenotypeRepository.save(sample_name, kg_variant['id'], v['genotype'] or './.')

    # Sort by clinical priority
    order = {'clinical_action': 0, 'pharmacogenomics': 1, 'disease_risk': 2, 'carrier_status': 3}
    findings.sort(key=lambda x: (order.get(x.get('category', ''), 99), -x['score']['total_score']))

    # v3.0: Build health timeline
    HealthTimeline.auto_build_from_analysis(sample_name, findings, profile, health_data, hospital_files)

    # v3.0: Calculate family risks
    family_risks = FamilyGraph.calculate_family_risks(sample_name, findings)

    # v3.0: Check for longitudinal alerts
    alert_count = GenomeMemoryEngine.process_clinvar_update(sample_name, snapshot_id=1)

    results = {
        "sample_name": sample_name,
        "total_vcf_variants": total,
        "reported": len(findings),
        "findings": findings,
        "profile": profile,
        "health_data": health_data,
        "hospital_files": hospital_files,
        "family_risks": family_risks,
        "new_alerts": alert_count,
        "timestamp": datetime.now().isoformat(),
    }

    # Save reports
    json_path = REPORT / "report_v3.json"
    json.dump(results, open(json_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)

    html_path = REPORT / "report_v3.html"
    html_path.write_text(generate_html_report(results), encoding='utf-8')

    return jsonify({"success": True, "reported": len(findings), "redirect": "/reports/report_v3.html"})


# ============================================================
# v3.0 API: Longitudinal Memory
# ============================================================
@app.route("/api/alerts/<sample_name>")
def get_alerts(sample_name):
    unread_only = request.args.get('unread', 'false').lower() == 'true'
    alerts = LongitudinalMemory.get_alerts(sample_name, unread_only)
    return jsonify({"alerts": alerts, "count": len(alerts)})

@app.route("/api/alerts/<int:alert_id>/read", methods=["POST"])
def mark_alert_read(alert_id):
    LongitudinalMemory.mark_alert_read(alert_id)
    return jsonify({"success": True})

@app.route("/api/variant_history/<sample_name>")
def variant_history(sample_name):
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT vh.*, v.chromosome, v.position, g.symbol as gene_symbol
            FROM variant_history vh
            JOIN variants v ON vh.variant_id = v.id
            LEFT JOIN genes g ON v.gene_id = g.id
            JOIN user_genotypes ug ON v.id = ug.variant_id
            WHERE ug.sample_name = ?
            ORDER BY vh.changed_at DESC
        """, (sample_name,)).fetchall()
        return jsonify({"history": [dict(r) for r in rows]})


# ============================================================
# v3.0 API: Health Timeline
# ============================================================
@app.route("/api/timeline/<sample_name>")
def get_timeline(sample_name):
    event_types = request.args.get('types', '').split(',') if request.args.get('types') else None
    start = request.args.get('start')
    end = request.args.get('end')
    events = HealthTimeline.get_timeline(sample_name, event_types, start, end)
    return jsonify({"events": events, "count": len(events)})

@app.route("/api/timeline/<sample_name>/risk")
def get_risk_timeline(sample_name):
    gene = request.args.get('gene')
    events = HealthTimeline.get_risk_timeline(sample_name, gene)
    return jsonify({"events": events})


# ============================================================
# v3.0 API: Family Graph
# ============================================================
@app.route("/api/family/<proband_sample>")
def get_family(proband_sample):
    family = FamilyGraph.get_family(proband_sample)
    risks = FamilyGraph.get_family_risks(proband_sample)
    pedigree = FamilyGraph.get_pedigree_data(proband_sample)
    return jsonify({
        "family": family,
        "risks": risks,
        "pedigree": pedigree
    })

@app.route("/api/family/<proband_sample>/member", methods=["POST"])
def add_family_member(proband_sample):
    data = request.json or {}
    member_id = FamilyGraph.add_member(
        proband_sample=proband_sample,
        relation=data.get('relation'),
        name=data.get('name'),
        sex=data.get('sex'),
        affected=data.get('affected', False),
        conditions=data.get('conditions', []),
        has_genome=data.get('has_genome', False),
        sample_name=data.get('sample_name')
    )
    return jsonify({"success": True, "member_id": member_id})

@app.route("/api/family/<proband_sample>/calculate", methods=["POST"])
def calculate_family_risks(proband_sample):
    findings = request.json.get('findings', [])
    risks = FamilyGraph.calculate_family_risks(proband_sample, findings)
    return jsonify({"risks": risks, "count": len(risks)})


# ============================================================
# v3.0 API: Medication Check
# ============================================================
@app.route("/api/medication/check/<sample_name>", methods=["POST"])
def check_medication(sample_name):
    data = request.json or {}
    drug_name = data.get('drug_name', '')
    conflicts = GenomeMemoryEngine.check_medication_conflicts(sample_name, drug_name)
    return jsonify({"drug": drug_name, "conflicts": conflicts, "has_conflict": len(conflicts) > 0})


# ============================================================
# HTML Report Generator v3.0 — Interactive Dashboard
# ============================================================
def generate_html_report(data: dict) -> str:
    findings = data.get('findings', [])
    profile = data.get('profile')
    health = data.get('health_data')
    hospitals = data.get('hospital_files', [])
    family_risks = data.get('family_risks', [])
    alerts = data.get('new_alerts', 0)
    sample_name = data.get('sample_name', 'default')
    total = data.get('total_vcf_variants', 0)
    ts = data.get('timestamp', '')[:10]

    # ---- counts ----
    cats = {}
    for f in findings:
        c = f.get('category_cn', 'Other')
        cats[c] = cats.get(c, 0) + 1
    high_priority = sum(1 for f in findings if f.get('urgency') == 'high')

    # ---- top finding for alert card ----
    top = findings[0] if findings else None

    # ---- reasoning chain HTML ----
    chain_nodes = []
    if top:
        chain_nodes.append(('Variant', 'chr%s:%s' % (top.get('chrom',''), top.get('pos','')), '#e6fffb', '#0f766e'))
        chain_nodes.append((top.get('gene_symbol','Gene'), top.get('hgvs_protein','') or top.get('hgvs_coding',''), '#e6fffb', '#0f766e'))
        chain_nodes.append(('Disease', top.get('disease_name','Hereditary Condition'), '#fff7ed', '#c2410c'))
        chain_nodes.append(('Action', 'Clinical Context', '#f0fdf4', '#15803d'))
    else:
        chain_nodes = [('Variant','chr7 C>T','#e6fffb','#0f766e'),('PRSS1','p.Ala16Val','#e6fffb','#0f766e'),('Disease','Hereditary Pancreatitis','#fff7ed','#c2410c'),('Action','Clinical Context','#f0fdf4','#15803d')]

    chain_html = '<div class="chain">'
    for i, (label, val, bg, color) in enumerate(chain_nodes):
        chain_html += '<div class="node" style="background:%s;color:%s">%s<br><b>%s</b></div>' % (bg, color, label, val)
        if i < len(chain_nodes) - 1:
            chain_html += '<div class="arrow">→</div>'
    chain_html += '</div>'

    # ---- findings cards ----
    cards_html = []
    for f in findings:
        gene = f.get('gene_symbol', 'Unknown')
        score = f['score']['total_score']
        urgency = f.get('urgency', 'none')
        urgency_color = {'high': '#ef4444', 'medium': '#f97316', 'low': '#eab308', 'none': '#64748b'}
        ucolor = urgency_color.get(urgency, '#64748b')
        actions = ''.join('<li>%s</li>' % a for a in f.get('recommendations', []))

        # drug block
        drug_block = ''
        if f.get('drug_database'):
            db = f['drug_database']
            drugs = ''.join(
                '<div class="drug-item"><b>%s</b> <span style="color:#c2410c">%s</span><br>%s <span style="color:#94a3b8;font-size:11px">[%s]</span></div>'
                % (d['drug'], d['effect'], d['recommendation'], d['source'])
                for d in db.get('drugs', [])
            )
            drug_block = '<div class="drug-panel">%s</div>' % drugs

        card = '<div class="finding-card">'
        card += '<div class="finding-header">'
        card += '<div class="finding-title">%s</div>' % gene
        card += '<div class="finding-meta">Chr%s:%s · %s→%s · %s</div>' % (
            f.get("chrom",""), f.get("pos",""), f.get("ref",""), f.get("alt",""), f.get("zygosity",""))
        card += '<div class="finding-score" style="color:%s">%s</div>' % (ucolor, score)
        card += '</div>'
        card += '<div class="tags">'
        card += '<span class="tag">%s</span>' % f.get("category_cn","")
        card += '<span class="tag">%s</span>' % f.get("clinvar_significance","")
        card += '<span class="tag">%s</span>' % f.get("inheritance",{}).get("pattern_name","")
        card += '</div>'
        card += '<p class="finding-desc">%s</p>' % f.get("description","")
        card += '<div class="actions"><b>Recommended Actions:</b><ul>%s</ul></div>' % actions
        card += drug_block
        card += '</div>'
        cards_html.append(card)

    # ---- timeline from DB ----
    timeline_html = ''
    try:
        events = HealthTimeline.get_timeline(sample_name)[:6]
        if events:
            timeline_html = '<div class="timeline">'
            for e in events:
                etype = e.get('event_type', '')
                color = {'genome':'#ef4444','wearable':'#3b82f6','symptom':'#f97316','milestone':'#a78bfa','lab':'#10b981','medication':'#f59e0b','imaging':'#6366f1'}.get(etype, '#64748b')
                timeline_html += '<div class="timeline-item">'
                timeline_html += '<div class="timeline-dot" style="background:%s"></div>' % color
                timeline_html += '<div class="timeline-date">%s · %s</div>' % (e.get('event_date',''), etype.upper())
                timeline_html += '<div class="timeline-title">%s</div>' % e.get('title','')
                if e.get('description'):
                    timeline_html += '<div class="timeline-desc">%s</div>' % e.get('description','')
                timeline_html += '</div>'
            timeline_html += '</div>'
    except Exception:
        timeline_html = '<div class="timeline"><div class="timeline-item"><div class="timeline-dot"></div><div class="timeline-date">2026 · GENOME</div><div class="timeline-title">Initial genome analysis</div></div></div>'

    # ---- family graph ----
    family_html = ''
    if family_risks:
        family_html = '<div class="family-list">'
        for r in family_risks:
            risk_color = '#ef4444' if r['probability'] >= 0.5 else '#f97316' if r['probability'] >= 0.25 else '#eab308'
            family_html += '<div class="family-item" style="border-left-color:%s">' % risk_color
            family_html += '<b>%s</b> · %s<br>' % (r['relation'], r['gene_symbol'])
            family_html += '<span style="color:%s">Risk: %.0f%% (%s)</span><br>' % (risk_color, r['probability']*100, r['risk_type'])
            family_html += '<small>%s</small>' % r['recommendation']
            family_html += '</div>'
        family_html += '</div>'
    else:
        family_html = '<p class="small">No family members added yet. Use the API to build your pedigree.</p>'

    # ---- phenotype matching ----
    phenotype_html = ''
    if profile:
        conditions = profile.get('conditions', [])
        family_hist = profile.get('family_history', [])
        if conditions or family_hist:
            phenotype_html += '<div class="pheno-tags">'
            for c in conditions:
                phenotype_html += '<span class="pheno-tag">%s</span>' % c
            for fh in family_hist:
                phenotype_html += '<span class="pheno-tag">%s: %s</span>' % (fh.get('relation',''), fh.get('condition',''))
            phenotype_html += '</div>'
            # match findings to phenotype
            matched = []
            for f in findings:
                if f.get('personal_context') and f['personal_context'].get('matched_factors'):
                    matched.append(f)
            if matched:
                phenotype_html += '<p style="margin-top:10px"><b>%d variants</b> match your phenotype profile.</p>' % len(matched)
    if not phenotype_html:
        phenotype_html = '<p class="small">Upload a health profile to enable phenotype matching.</p>'

    # ---- medication intelligence ----
    med_html = ''
    med_genes = [f for f in findings if f.get('drug_database')]
    if med_genes:
        med_html = '<div class="med-list">'
        for f in med_genes[:3]:
            db = f['drug_database']
            for d in db.get('drugs', [])[:2]:
                med_html += '<div class="med-item">'
                med_html += '<b>%s</b> <span style="color:#c2410c">%s</span>' % (d['drug'], d['effect'])
                med_html += '<br><small>%s</small>' % d['recommendation']
                med_html += '</div>'
        med_html += '</div>'
    else:
        med_html = '<p class="small">No pharmacogenomic variants detected in this analysis.</p>'

    # ---- alerts ----
    alert_banner = ''
    if alerts > 0:
        alert_banner = '<div class="alert-banner"><b>Important Updates:</b> %d new alert(s) detected. <a href="/api/alerts/%s">View Alerts →</a></div>' % (alerts, sample_name)
    elif top and top.get('clinvar_significance') in ('Pathogenic', 'Likely_pathogenic'):
        alert_banner = '<div class="alert-banner"><b>Important Finding:</b> %s variant detected with pathogenic evidence. Review recommended.</div>' % top.get('gene_symbol','')

    # ---- health metrics ----
    health_html = ''
    if health and not health.get('error'):
        metrics = health.get('latest_metrics', {})
        if metrics:
            health_html = '<div class="health-grid">'
            for name, m in list(metrics.items())[:6]:
                health_html += '<div class="health-cell"><div class="health-name">%s</div><div class="health-val">%.1f</div><div class="health-unit">%s</div></div>' % (name, m['value'], m.get('unit',''))
            health_html += '</div>'

    # ---- Build full page ----
    page = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Personal Genome Intelligence Report</title>
<style>
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#f6f8f7;color:#1d2939;margin:0;padding:0}}
.container{{max-width:1200px;margin:0 auto;padding:32px 20px}}
.header{{display:flex;justify-content:space-between;align-items:center;margin-bottom:28px;flex-wrap:wrap;gap:12px}}
.logo{{font-size:24px;font-weight:700;color:#0f766e;display:flex;align-items:center;gap:8px}}
.nav{{display:flex;gap:8px;flex-wrap:wrap}}
.nav a{{color:#667085;text-decoration:none;font-size:13px;padding:6px 14px;background:#fff;border-radius:20px;box-shadow:0 1px 3px rgba(0,0,0,.06)}}
.nav a:hover{{color:#0f766e}}
.grid{{display:grid;grid-template-columns:300px 1fr;gap:24px}}
@media(max-width:900px){{.grid{{grid-template-columns:1fr}}}}
.card{{background:#fff;border-radius:20px;padding:24px;box-shadow:0 8px 30px rgba(0,0,0,.06);margin-bottom:20px}}
.card h3{{font-size:15px;font-weight:600;color:#1d2939;margin-bottom:14px}}
.metric{{font-size:36px;font-weight:700;color:#0f766e;line-height:1}}
.small{{color:#667085;font-size:13px}}
.tag{{display:inline-block;background:#ecfdf3;color:#027a48;padding:4px 10px;border-radius:20px;font-size:12px;margin:2px 4px 2px 0}}
.tag-orange{{background:#fff7ed;color:#c2410c}}
.tag-blue{{background:#eff6ff;color:#1d4ed8}}
.tag-red{{background:#fef2f2;color:#b91c1c}}
.chain{{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-top:16px}}
.node{{padding:12px 16px;border-radius:14px;background:#e6fffb;border:1px solid #99f6e4;font-size:13px;text-align:center;min-width:90px}}
.node b{{display:block;font-size:14px;margin-top:2px}}
.arrow{{color:#94a3b8;font-size:20px}}
.alert-banner{{border-left:5px solid #f97316;background:#fff7ed;padding:16px 20px;border-radius:0 12px 12px 0;margin-bottom:20px}}
.alert-banner a{{color:#c2410c;text-decoration:none;font-weight:600}}
.timeline{{border-left:3px solid #cbd5e1;padding-left:18px;margin-top:10px}}
.timeline-item{{position:relative;margin:14px 0;padding-left:14px}}
.timeline-dot{{position:absolute;left:-26px;top:4px;width:10px;height:10px;border-radius:50%;background:#0f766e}}
.timeline-date{{font-size:11px;color:#667085;text-transform:uppercase;letter-spacing:.5px}}
.timeline-title{{font-size:13px;font-weight:600;color:#1d2939;margin-top:2px}}
.timeline-desc{{font-size:12px;color:#667085;margin-top:2px}}
.family-list{{margin-top:8px}}
.family-item{{padding:10px 14px;background:#f8fafc;border-radius:10px;margin-bottom:8px;border-left:3px solid #cbd5e1;font-size:13px}}
.finding-card{{background:#fff;border-radius:16px;padding:20px;margin-bottom:14px;box-shadow:0 2px 12px rgba(0,0,0,.04)}}
.finding-header{{display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:8px;margin-bottom:10px}}
.finding-title{{font-size:18px;font-weight:700;color:#1d2939}}
.finding-meta{{font-size:12px;color:#667085}}
.finding-score{{font-size:28px;font-weight:700}}
.tags{{margin-bottom:10px}}
.finding-desc{{color:#475569;font-size:14px;line-height:1.6;margin:8px 0}}
.actions{{font-size:13px;color:#475569}}
.actions ul{{margin:6px 0;padding-left:18px}}
.actions li{{margin:4px 0}}
.drug-panel{{margin-top:12px;padding:12px;background:#fff7ed;border-radius:10px}}
.drug-item{{font-size:13px;padding:6px 0;border-bottom:1px solid #fed7aa}}
.drug-item:last-child{{border-bottom:none}}
.pheno-tags{{display:flex;flex-wrap:wrap;gap:6px;margin-top:8px}}
.pheno-tag{{background:#f3f4f6;color:#374151;padding:4px 10px;border-radius:20px;font-size:12px}}
.med-list{{margin-top:8px}}
.med-item{{padding:10px;background:#f0fdf4;border-radius:10px;margin-bottom:8px;font-size:13px}}
.health-grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-top:10px}}
.health-cell{{background:#f8fafc;border-radius:10px;padding:12px;text-align:center}}
.health-name{{font-size:11px;color:#667085}}
.health-val{{font-size:20px;font-weight:700;color:#0f766e;margin-top:4px}}
.health-unit{{font-size:10px;color:#94a3b8}}
.graph-placeholder{{height:120px;background:radial-gradient(circle,#99f6e4 2px,transparent 3px);background-size:35px 35px;border-radius:15px;margin-top:10px;position:relative;overflow:hidden}}
.graph-placeholder::after{{content:'Knowledge Graph Visualization';position:absolute;inset:0;display:flex;align-items:center;justify-content:center;color:#0f766e;font-size:14px;font-weight:600;opacity:.6}}
.footer{{margin-top:40px;padding:20px;text-align:center;font-size:12px;color:#94a3b8}}
</style>
</head>
<body>
<div class="container">
<div class="header">
  <div class="logo">🧬 Genome Intelligence</div>
  <div class="nav">
    <a href="/">Dashboard</a>
    <a href="#findings">Findings</a>
    <a href="#medication">Medication</a>
    <a href="#memory">Memory</a>
    <a href="/api/report" target="_blank">JSON</a>
  </div>
</div>

{alert_banner}

<div class="grid">
<div>
  <div class="card">
    <h3>Your Genome</h3>
    <div class="metric">{total:,}</div>
    <div class="small">variants analyzed</div>
    <br>
    <b>{len(findings)} findings</b>
    <p><span class="tag">{high_priority} High Priority</span></p>
    <p class="small">Last knowledge update<br>{ts}</p>
  </div>

  <div class="card">
    <h3>Longitudinal Genome Memory</h3>
    {timeline_html}
  </div>

  <div class="card">
    <h3>Family Graph</h3>
    {family_html}
  </div>

  {f'<div class="card"><h3>Apple Health</h3>{health_html}</div>' if health_html else ''}
</div>

<div>
  <div class="card" id="findings">
    <h2 style="margin:0 0 8px 0;font-size:18px">AI Medical Reasoning Engine</h2>
    <p class="small">From raw variant to personal medical meaning</p>
    {chain_html}
  </div>

  {f"""<div class="card alert-banner" style="margin-bottom:20px">
    <h3 style="margin:0 0 8px 0">Important Finding</h3>
    <b>{top.get('gene_symbol','')} {top.get('hgvs_coding','') or top.get('hgvs_protein','')}</b>
    <p>Evidence: {top.get('clinvar_significance','')}</p>
    <p class="small">Reasoning: Variant + gene function + disease database + phenotype matching</p>
    <p class="small">Next: review with genetic counselor if clinically relevant</p>
  </div>""" if top else ''}

  <div class="card">
    <h3>Phenotype Matching</h3>
    <p class="small">Input: symptoms, family history, labs</p>
    <p class="small">AI matches possible gene-disease relationships.</p>
    {phenotype_html}
  </div>

  <div class="card" id="medication">
    <h3>Medication Intelligence</h3>
    <p class="small">Before medication: check DPYD / CYP / VKORC1 related risks.</p>
    {med_html}
  </div>

  <div class="card">
    <h3>Medical Knowledge Graph</h3>
    <div class="graph-placeholder"></div>
    <p class="small" style="margin-top:8px">Gene ↔ Disease ↔ Drug ↔ Phenotype network</p>
  </div>

  <div id="findings">
    <h2 style="font-size:18px;margin:24px 0 12px">Detailed Findings</h2>
    {''.join(cards_html)}
  </div>
</div>
</div>

<div class="footer">
  <p>⚠️ This report is for educational and research purposes only. It does not replace professional medical advice.</p>
  <p>DNA Personal Genome Intelligence v3.0 · ClinVar Knowledge Graph · CPIC/PharmGKB · Longitudinal Memory · Family Graph</p>
</div>
</div>
</body>
</html>"""
    return page

@app.route("/reports/<path:filename>")
def serve_report(filename):
    return send_from_directory(REPORT, filename)


@app.route("/api/report")
def report_api():
    r = REPORT / "report_v3.json"
    if r.exists():
        return jsonify(json.load(open(r, encoding='utf-8')))
    return jsonify({"findings": []})


if __name__ == "__main__":
    print("=" * 50)
    print("DNA Genome Intelligence v3.0")
    print("Knowledge Graph + Reasoning + Longitudinal Memory + Timeline + Family")
    print("Open: http://localhost:5001")
    print("=" * 50)
    app.run(debug=False, port=5001, host='0.0.0.0')
