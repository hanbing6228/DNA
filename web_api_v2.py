#!/usr/bin/env python3
"""
DNA Personal Genome Intelligence v2.1
- Knowledge Graph + Reasoning Engine
- Apple Health XML parsing
- Hospital report storage
- Enhanced drug database (CPIC/PharmGKB common pairs)
- Phenotype matching display
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

app = Flask(__name__, template_folder=str(BASE / "templates"))
UPLOAD = BASE / "uploads"
REPORT = BASE / "reports"
UPLOAD.mkdir(exist_ok=True)
REPORT.mkdir(exist_ok=True)
app.config["MAX_CONTENT_LENGTH"] = 500 * 1024 * 1024

init_db()

# ============================================================
# Drug Database (CPIC / PharmGKB common pairs)
# ============================================================
DRUG_DB = {
    'MTHFR': {
        'drugs': [
            {'drug': 'Methotrexate', 'effect': '可能增加毒性风险', 'recommendation': '考虑降低剂量或监测血药浓度', 'source': 'CPIC'},
            {'drug': '5-Fluorouracil (5-FU)', 'effect': '可能增加毒性', 'recommendation': '谨慎使用，密切监测', 'source': 'CPIC'},
            {'drug': 'Folic acid supplements', 'effect': '可能需要补充', 'recommendation': '咨询医生是否需要活性叶酸', 'source': 'PharmGKB'},
        ],
        'description': 'MTHFR 基因编码亚甲基四氢叶酸还原酶，影响叶酸代谢和多种药物反应。'
    },
    'DPYD': {
        'drugs': [
            {'drug': '5-Fluorouracil (5-FU)', 'effect': '严重毒性风险', 'recommendation': '禁忌或大幅减量，必须基因检测', 'source': 'CPIC'},
            {'drug': 'Capecitabine', 'effect': '严重毒性风险', 'recommendation': '禁忌或大幅减量', 'source': 'CPIC'},
            {'drug': 'Tegafur', 'effect': '毒性风险增加', 'recommendation': '避免使用', 'source': 'CPIC'},
        ],
        'description': 'DPYD 基因编码二氢嘧啶脱氢酶，是氟尿嘧啶类药物代谢的关键酶。'
    },
    'CYP2D6': {
        'drugs': [
            {'drug': 'Codeine', 'effect': '可能无效或超快代谢', 'recommendation': '避免使用，换用其他镇痛药', 'source': 'CPIC'},
            {'drug': 'Tamoxifen', 'effect': '疗效可能降低', 'recommendation': '考虑替代内分泌治疗', 'source': 'CPIC'},
            {'drug': 'Tramadol', 'effect': '代谢变异', 'recommendation': '监测疗效，必要时调整', 'source': 'PharmGKB'},
        ],
        'description': 'CYP2D6 是重要的药物代谢酶，影响多种药物的血药浓度。'
    },
    'CYP2C19': {
        'drugs': [
            {'drug': 'Clopidogrel (Plavix)', 'effect': '可能抗血小板效果不足', 'recommendation': '考虑换用替格瑞洛或普拉格雷', 'source': 'CPIC'},
            {'drug': 'Omeprazole', 'effect': '疗效可能增强', 'recommendation': '标准剂量通常安全', 'source': 'PharmGKB'},
            {'drug': 'Diazepam', 'effect': '代谢减慢', 'recommendation': '考虑减量', 'source': 'PharmGKB'},
        ],
        'description': 'CYP2C19 影响氯吡格雷等药物的代谢，与心血管治疗密切相关。'
    },
    'CYP2C9': {
        'drugs': [
            {'drug': 'Warfarin', 'effect': '出血风险增加', 'recommendation': '降低起始剂量，密切监测 INR', 'source': 'CPIC'},
            {'drug': 'Phenytoin', 'effect': '毒性风险', 'recommendation': '起始剂量减半', 'source': 'CPIC'},
            {'drug': 'Celecoxib', 'effect': '暴露量增加', 'recommendation': '最低有效剂量', 'source': 'PharmGKB'},
        ],
        'description': 'CYP2C9 参与华法林等药物的代谢，变异显著影响抗凝治疗。'
    },
    'VKORC1': {
        'drugs': [
            {'drug': 'Warfarin', 'effect': '华法林敏感性增加', 'recommendation': '显著降低起始剂量', 'source': 'CPIC'},
        ],
        'description': 'VKORC1 是华法林的作用靶点，变异影响抗凝敏感性。'
    },
    'SLCO1B1': {
        'drugs': [
            {'drug': 'Simvastatin', 'effect': '肌病风险增加', 'recommendation': '考虑低剂量或换用其他他汀', 'source': 'CPIC'},
            {'drug': 'Atorvastatin', 'effect': '轻度风险增加', 'recommendation': '监测肌酸激酶', 'source': 'PharmGKB'},
        ],
        'description': 'SLCO1B1 影响他汀类药物的肝脏摄取，与肌病风险相关。'
    },
    'TPMT': {
        'drugs': [
            {'drug': 'Azathioprine', 'effect': '严重骨髓抑制风险', 'recommendation': '大幅减量或避免使用', 'source': 'CPIC'},
            {'drug': '6-Mercaptopurine', 'effect': '严重骨髓抑制风险', 'recommendation': '大幅减量', 'source': 'CPIC'},
            {'drug': 'Thioguanine', 'effect': '毒性风险', 'recommendation': '大幅减量', 'source': 'CPIC'},
        ],
        'description': 'TPMT 缺乏会导致硫嘌呤类药物的严重毒性，用药前必须检测。'
    },
    'HLA-B': {
        'drugs': [
            {'drug': 'Carbamazepine', 'effect': 'Stevens-Johnson 综合征风险', 'recommendation': 'HLA-B*15:02 阳性者禁用', 'source': 'CPIC'},
            {'drug': 'Allopurinol', 'effect': '严重皮肤反应风险', 'recommendation': 'HLA-B*58:01 阳性者慎用', 'source': 'CPIC'},
        ],
        'description': 'HLA-B 等位基因与多种药物的严重皮肤不良反应相关。'
    },
    'CFTR': {
        'drugs': [
            {'drug': 'Ivacaftor', 'effect': '针对特定突变有效', 'recommendation': '需确认具体突变类型', 'source': 'FDA'},
        ],
        'description': 'CFTR 突变影响囊性纤维化治疗药物的响应。'
    },
}


def get_drug_guidance(gene_symbol: str) -> dict:
    """Get drug guidance for a gene from built-in database."""
    return DRUG_DB.get(gene_symbol.upper(), None)


# ============================================================
# Apple Health XML Parser
# ============================================================
def parse_apple_health(xml_path: Path) -> dict:
    """Parse Apple Health export.xml and extract key metrics."""
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

        # Extract latest values for key metrics
        key_types = {
            'HKQuantityTypeIdentifierHeartRate': '静息心率',
            'HKQuantityTypeIdentifierBloodPressureSystolic': '收缩压',
            'HKQuantityTypeIdentifierBloodPressureDiastolic': '舒张压',
            'HKQuantityTypeIdentifierBloodGlucose': '血糖',
            'HKQuantityTypeIdentifierBodyMassIndex': 'BMI',
            'HKQuantityTypeIdentifierBodyFatPercentage': '体脂率',
            'HKQuantityTypeIdentifierOxygenSaturation': '血氧饱和度',
            'HKQuantityTypeIdentifierStepCount': '步数',
            'HKQuantityTypeIdentifierDistanceWalkingRunning': '步行距离',
            'HKQuantityTypeIdentifierActiveEnergyBurned': '活动能量',
            'HKQuantityTypeIdentifierBasalEnergyBurned': '基础代谢',
            'HKQuantityTypeIdentifierSleepAnalysis': '睡眠',
        }

        latest = {}
        for r in records:
            short = r['type'].replace('HKQuantityTypeIdentifier', '').replace('HKCategoryTypeIdentifier', '')
            name = key_types.get(r['type'], short)
            if name not in latest or (r['date'] and r['date'] > latest[name]['date']):
                latest[name] = r

        # Calculate averages for trend metrics
        trends = {}
        for name, r in latest.items():
            trends[name] = {
                'value': r['value'],
                'unit': r['unit'],
                'date': r['date']
            }

        return {
            'record_count': len(records),
            'latest_metrics': trends,
            'summary': f"解析了 {len(records)} 条健康记录，提取了 {len(trends)} 项关键指标。"
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
        return jsonify({"error": "请上传VCF文件"}), 400

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

        # Enhanced drug guidance from built-in database
        gene = finding.get('gene_symbol', '')
        if gene:
            drug_info = get_drug_guidance(gene)
            if drug_info:
                finding['drug_database'] = drug_info
                # Merge with existing drug_guidance
                if 'drug_guidance' not in finding or not finding['drug_guidance']:
                    finding['drug_guidance'] = drug_info

        if finding['score']['total_score'] >= min_s and finding['category'] != 'research_vus':
            findings.append(finding)
            if kg_variant.get('id'):
                UserGenotypeRepository.save(sample_name, kg_variant['id'], v['genotype'] or './.')

    # Sort by clinical priority
    order = {'clinical_action': 0, 'pharmacogenomics': 1, 'disease_risk': 2, 'carrier_status': 3}
    findings.sort(key=lambda x: (order.get(x.get('category', ''), 99), -x['score']['total_score']))

    results = {
        "total_vcf_variants": total,
        "reported": len(findings),
        "findings": findings,
        "profile": profile,
        "health_data": health_data,
        "hospital_files": hospital_files,
        "timestamp": datetime.now().isoformat(),
    }

    # Save reports
    json_path = REPORT / "report_v2.json"
    json.dump(results, open(json_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)

    html_path = REPORT / "report_v2.html"
    html_path.write_text(generate_html_report(results), encoding='utf-8')

    return jsonify({"success": True, "reported": len(findings), "redirect": "/reports/report_v2.html"})


# ============================================================
# HTML Report Generator
# ============================================================
def generate_html_report(data: dict) -> str:
    findings = data.get('findings', [])
    profile = data.get('profile')
    health = data.get('health_data')
    hospitals = data.get('hospital_files', [])

    # Category counts
    cats = {}
    for f in findings:
        c = f.get('category_cn', '其他')
        cats[c] = cats.get(c, 0) + 1

    # Build finding cards
    cards_html = []
    for f in findings:
        gene = f.get('gene_symbol', '未知')
        score = f['score']['total_score']
        urgency_color = {'high': '#ef4444', 'medium': '#f97316', 'low': '#eab308', 'none': '#64748b'}
        color = urgency_color.get(f.get('urgency', 'none'), '#64748b')

        actions = ''.join('<li style="margin:6px 0">%s</li>' % a for a in f.get('recommendations', []))

        # Personal context
        personal_block = ''
        if f.get('personal_context'):
            pc = f['personal_context']
            factors = ''.join('<li style="margin:4px 0">%s</li>' % m for m in pc.get('matched_factors', []))
            personal_block = '<div style="margin-top:12px;padding:12px;background:#1e293b;border-radius:8px;border-left:3px solid #60a5fa">'
            personal_block += '<strong style="color:#60a5fa">👤 个人化评估</strong>'
            personal_block += '<p style="margin-top:6px;color:#94a3b8;font-size:13px">%s</p>' % pc['assessment']
            personal_block += '<ul style="color:#94a3b8;font-size:12px;margin-top:6px;padding-left:18px">%s</ul>' % factors
            personal_block += '</div>'

        # Drug database
        drug_block = ''
        if f.get('drug_database'):
            db = f['drug_database']
            drugs = ''.join(
                '<div style="margin:8px 0;padding:10px;background:#0f172a;border-radius:6px">'
                '<div style="font-weight:600;color:#e2e8f0;font-size:13px">%s</div>'
                '<div style="color:#f87171;font-size:12px;margin-top:2px">%s</div>'
                '<div style="color:#94a3b8;font-size:12px;margin-top:2px">%s</div>'
                '<div style="color:#64748b;font-size:11px;margin-top:2px">来源: %s</div>'
                '</div>' % (d['drug'], d['effect'], d['recommendation'], d['source'])
                for d in db.get('drugs', [])
            )
            drug_block = '<div style="margin-top:12px;padding:12px;background:#1e293b;border-radius:8px;border-left:3px solid #f97316">'
            drug_block += '<strong style="color:#f97316">💊 药物基因组学指导</strong>'
            drug_block += '<p style="margin-top:6px;color:#94a3b8;font-size:13px">%s</p>' % db.get('description', '')
            drug_block += drugs
            drug_block += '</div>'

        card = '<div style="background:#151e32;border-radius:16px;padding:24px;margin-bottom:16px;border:1px solid #1e293b">'
        card += '<div style="display:flex;align-items:center;gap:12px;margin-bottom:12px">'
        card += '<span style="font-size:24px">%s</span>' % f.get("icon","")
        card += '<div><div style="font-size:18px;font-weight:600">%s</div>' % gene
        card += '<div style="font-size:13px;color:#64748b">Chr%s:%s · %s→%s · %s</div></div>' % (
            f.get("chrom",""), f.get("pos",""), f.get("ref",""), f.get("alt",""), f.get("zygosity",""))
        card += '<div style="margin-left:auto;text-align:right">'
        card += '<div style="font-size:24px;font-weight:700;color:%s">%s</div>' % (color, score)
        card += '<div style="font-size:11px;color:#64748b">证据分</div></div></div>'
        card += '<div style="display:flex;gap:8px;margin-bottom:12px;flex-wrap:wrap">'
        card += '<span style="background:#1e293b;padding:4px 12px;border-radius:20px;font-size:12px">%s</span>' % f.get("category_cn","")
        card += '<span style="background:#1e293b;padding:4px 12px;border-radius:20px;font-size:12px">%s</span>' % f.get("clinvar_significance","")
        card += '<span style="background:#1e293b;padding:4px 12px;border-radius:20px;font-size:12px">%s</span>' % f.get("inheritance",{}).get("pattern_name","")
        card += '</div>'
        card += '<p style="color:#94a3b8;font-size:14px;line-height:1.6">%s</p>' % f.get("description","")
        card += '<div style="margin-top:12px"><strong style="color:#e2e8f0;font-size:13px">建议行动：</strong>'
        card += '<ul style="color:#94a3b8;font-size:13px;margin-top:6px;padding-left:20px">%s</ul></div>' % actions
        card += personal_block
        card += drug_block
        card += '</div>'
        cards_html.append(card)

    # Summary cards
    summary_html = []
    cat_colors = {"需要临床行动": "#ef4444", "药物基因组学": "#3b82f6", "疾病风险": "#f97316", "携带者状态": "#eab308"}
    for c, n in cats.items():
        summary_html.append('<div style="flex:1;background:#151e32;border-radius:16px;padding:20px;text-align:center;border:1px solid #1e293b;min-width:140px">')
        summary_html.append('<div style="font-size:32px;font-weight:700;color:%s">%s</div>' % (cat_colors.get(c, "#64748b"), n))
        summary_html.append('<div style="font-size:13px;color:#64748b;margin-top:4px">%s</div></div>' % c)

    # Profile section
    profile_section = ''
    if profile:
        basic = profile.get('basic', {})
        conditions = profile.get('conditions', [])
        meds = profile.get('medications', [])
        family = profile.get('family_history', [])

        profile_section = '<div style="background:#151e32;border-radius:16px;padding:20px;margin-bottom:20px;border:1px solid #1e293b">'
        profile_section += '<h3 style="margin-bottom:12px;font-size:16px">👤 个人健康档案</h3>'
        if basic:
            profile_section += '<p style="color:#94a3b8;font-size:13px">年龄: %s · 性别: %s</p>' % (basic.get('age', '-'), basic.get('sex', '-'))
        if conditions:
            profile_section += '<div style="margin-top:8px"><span style="color:#64748b;font-size:12px">现有症状/疾病: </span>%s</div>' % ', '.join(
                '<span style="background:#1e293b;padding:2px 8px;border-radius:10px;font-size:12px">%s</span>' % c for c in conditions
            )
        if meds:
            profile_section += '<div style="margin-top:8px"><span style="color:#64748b;font-size:12px">当前用药: </span>%s</div>' % ', '.join(
                '<span style="background:#1e293b;padding:2px 8px;border-radius:10px;font-size:12px">%s</span>' % m for m in meds
            )
        if family:
            profile_section += '<div style="margin-top:8px"><span style="color:#64748b;font-size:12px">家族史: </span>%s</div>' % ', '.join(
                '<span style="background:#1e293b;padding:2px 8px;border-radius:10px;font-size:12px">%s(%s)</span>' % (fh.get('relation',''), fh.get('condition','')) for fh in family
            )
        profile_section += '</div>'

    # Health data section
    health_section = ''
    if health and not health.get('error'):
        metrics = health.get('latest_metrics', {})
        if metrics:
            health_section = '<div style="background:#151e32;border-radius:16px;padding:20px;margin-bottom:20px;border:1px solid #1e293b">'
            health_section += '<h3 style="margin-bottom:12px;font-size:16px">🍎 Apple Health 指标</h3>'
            health_section += '<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(140px,1fr));gap:10px">'
            for name, m in list(metrics.items())[:8]:
                health_section += '<div style="background:#0f172a;padding:10px;border-radius:8px;text-align:center">'
                health_section += '<div style="font-size:11px;color:#64748b">%s</div>' % name
                health_section += '<div style="font-size:18px;font-weight:600;color:#60a5fa;margin-top:4px">%.1f</div>' % m['value']
                health_section += '<div style="font-size:10px;color:#64748b">%s</div>' % m.get('unit', '')
                health_section += '</div>'
            health_section += '</div></div>'

    # Hospital files section
    hospital_section = ''
    if hospitals:
        hospital_section = '<div style="background:#151e32;border-radius:16px;padding:20px;margin-bottom:20px;border:1px solid #1e293b">'
        hospital_section += '<h3 style="margin-bottom:12px;font-size:16px">🏥 已上传医院报告</h3>'
        hospital_section += '<div style="display:flex;flex-wrap:wrap;gap:8px">'
        for h in hospitals:
            hospital_section += '<span style="background:#0f172a;padding:6px 12px;border-radius:8px;font-size:12px">📄 %s</span>' % h
        hospital_section += '</div></div>'

    # Build page
    page = []
    page.append('<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8">')
    page.append('<meta name="viewport" content="width=device-width,initial-scale=1.0">')
    page.append('<title>DNA Report v2.1</title>')
    page.append('<style>body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;background:#0b1120;color:#e2e8f0;margin:0;padding:0}')
    page.append('.container{max-width:900px;margin:0 auto;padding:40px 20px}')
    page.append('h1{font-size:28px;margin-bottom:8px}h2{font-size:20px;margin:24px 0 12px}')
    page.append('.subtitle{color:#64748b;margin-bottom:24px;font-size:14px}')
    page.append('.summary{display:flex;gap:12px;margin-bottom:24px;flex-wrap:wrap}')
    page.append('</style></head><body><div class="container">')
    page.append('<h1>🧬 个人基因组智能报告</h1>')
    page.append('<p class="subtitle">知识图谱 v2.1 · %s · 共分析 %s 个变异 · 发现 %s 条相关</p>' % (
        data.get("timestamp","")[:10], data.get("total_vcf_variants",0), len(findings)))

    page.append('<div class="summary">%s</div>' % ''.join(summary_html))
    page.append(profile_section)
    page.append(health_section)
    page.append(hospital_section)
    page.append(''.join(cards_html))

    page.append('<div style="margin-top:40px;padding:20px;background:#151e32;border-radius:12px;border:1px solid #1e293b;font-size:12px;color:#64748b;text-align:center">')
    page.append('<p>⚠️ 本报告仅供教育和研究参考，不能替代专业医疗建议。</p>')
    page.append('<p style="margin-top:8px">DNA Personal Genome Intelligence v2.1 · 基于 ClinVar 知识图谱 · CPIC/PharmGKB 药物指导</p>')
    page.append('</div></div></body></html>')

    return ''.join(page)


@app.route("/reports/<path:filename>")
def serve_report(filename):
    return send_from_directory(REPORT, filename)


@app.route("/api/report")
def report_api():
    r = REPORT / "report_v2.json"
    if r.exists():
        return jsonify(json.load(open(r, encoding='utf-8')))
    return jsonify({"findings": []})


if __name__ == "__main__":
    print("=" * 50)
    print("🧬 DNA Genome Intelligence v2.1")
    print("知识图谱 + 规则推理 + 药物数据库 + 健康数据")
    print("打开浏览器访问: http://localhost:5001")
    print("=" * 50)
    app.run(debug=False, port=5001, host='0.0.0.0')
