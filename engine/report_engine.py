import json
from datetime import datetime
from pathlib import Path

class ReportEngine:
    """高级医疗报告生成引擎"""

    @staticmethod
    def generate_json(results, output_path):
        report = {
            'generated_at': datetime.now().isoformat(),
            'version': '0.4',
            'summary': {
                'total_variants': results.get('total', 0),
                'reported_findings': len(results.get('variants', [])),
            },
            'findings': results.get('variants', []),
        }
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        return report

    @staticmethod
    def generate_html(results, output_path):
        variants = results.get('variants', [])
        total = results.get('total', 0)

        groups = {k: [] for k in ['clinical_action', 'disease_risk', 'pharmacogenomics', 'carrier_status', 'research_vus']}
        for v in variants:
            cat = v.get('category', 'research_vus')
            groups[cat].append(v)

        html_parts = []
        html_parts.append('<!DOCTYPE html>')
        html_parts.append('<html lang="zh-CN"><head>')
        html_parts.append('<meta charset="UTF-8">')
        html_parts.append('<meta name="viewport" content="width=device-width, initial-scale=1.0">')
        html_parts.append('<title>个人基因分析报告 v0.4</title>')
        html_parts.append('<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">')
        html_parts.append('<link rel="stylesheet" href="../static/style.css">')
        html_parts.append('</head><body>')

        html_parts.append(ReportEngine._render_header(total, len(variants)))
        html_parts.append(ReportEngine._render_stats(groups))

        html_parts.append(ReportEngine._render_section('clinical_action', groups['clinical_action'], '需要临床行动', 'critical', '#ef4444', 'rgba(239,68,68,0.15)'))
        html_parts.append(ReportEngine._render_section('pharmacogenomics', groups['pharmacogenomics'], '药物基因组学', 'pharma', '#3b82f6', 'rgba(59,130,246,0.15)'))
        html_parts.append(ReportEngine._render_section('disease_risk', groups['disease_risk'], '疾病风险', 'risk', '#f97316', 'rgba(249,115,22,0.15)'))
        html_parts.append(ReportEngine._render_section('carrier_status', groups['carrier_status'], '携带者状态', 'carrier', '#eab308', 'rgba(234,179,8,0.15)'))

        html_parts.append(ReportEngine._render_footer())
        html_parts.append('</body></html>')

        html = '\n'.join(html_parts)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)
        return html

    @staticmethod
    def _render_header(total, findings_count):
        now = datetime.now().strftime('%Y年%m月%d日')
        return '<div class="container">'
        + '<div class="report-header">'
        + '<div class="logo">&#129516;</div>'
        + '<h1>个人基因分析报告</h1>'
        + '<p class="subtitle">Personal Genome Intelligence Report</p>'
        + f'<p class="meta">生成日期：{now} · 共分析 {total:,} 个变异位点 · 发现 {findings_count} 个临床相关结果</p>'
        + '<div class="disclaimer">&#9888; 本报告仅供教育和研究参考，不能替代专业医疗建议</div>'
        + '</div>'

    @staticmethod
    def _render_stats(groups):
        stats = [
            ('clinical_action', '紧急', '#ef4444'),
            ('pharmacogenomics', '药物基因组', '#3b82f6'),
            ('disease_risk', '疾病风险', '#f97316'),
            ('carrier_status', '携带者', '#eab308'),
        ]
        cards = []
        for key, label, color in stats:
            count = len(groups.get(key, []))
            cards.append(f'<div class="stat-card" style="--accent-color:{color}"><div class="number">{count}</div><div class="label">{label}</div></div>')
        return '<div class="stats-grid">' + ''.join(cards) + '</div>'

    @staticmethod
    def _render_section(cat_key, variants, title, style_key, color, bg):
        if not variants:
            return ''
        icon_map = {'critical':'&#128308;', 'pharma':'&#128138;', 'risk':'&#128992;', 'carrier':'&#128993;'}
        icon = icon_map.get(style_key, '&#9898;')
        cards = [ReportEngine._render_variant_card(v, color) for v in variants]
        return f'<div class="section"><div class="section-header" style="--accent-color:{color};--accent-bg:{bg}"><div class="icon">{icon}</div><h2>{title}</h2><span class="count">{len(variants)}</span></div>{"".join(cards)}</div>'

    @staticmethod
    def _render_variant_card(v, accent_color):
        gene = v.get('gene_name', '未知基因')
        hgvs = v.get('hgvs_p') or v.get('hgvs_c', '')
        sig = v.get('significance', '未知')
        impact = v.get('impact', '')
        disease = v.get('disease', '')
        score = v.get('score', 0)
        summary = v.get('summary', '')
        desc = v.get('disease_description', '')
        recs = v.get('recommendations', [])
        inh = v.get('inheritance_assessment', {})
        zyg = inh.get('zygosity', '')
        zyg_cn = {'heterozygous':'杂合','homozygous_alt':'纯合','homozygous_ref':'野生型'}.get(zyg, zyg)
        affected = inh.get('affected_status', False)
        carrier = inh.get('carrier_status', False)
        act = v.get('actionability', {})
        actions = act.get('actions', [])
        surveillance = act.get('surveillance', [])
        lifestyle = act.get('lifestyle', [])
        drugs = act.get('drug_guidance', [])
        personal = v.get('personal_context', {})
        has_personal = personal and (personal.get('personalized_risk') or personal.get('personalized_advice'))

        parts = []
        parts.append(f'<div class="variant-card" style="--accent-color:{accent_color}">')
        parts.append(f'<div class="variant-header"><div class="variant-title">{gene}<span class="hgvs">{hgvs}</span></div></div>')
        parts.append(f'<div class="variant-meta">Chr{v.get("chrom","")}:{v.get("pos","")} · {v.get("ref","")} → {v.get("alt","")} · 基因型: {zyg_cn}</div>')

        parts.append('<div class="badges">')
        parts.append(f'<span class="badge badge-critical">{sig}</span>')
        if impact: parts.append(f'<span class="badge badge-high">{impact}</span>')
        parts.append(f'<span class="badge badge-gray">证据分 {score}</span>')
        if carrier and not affected: parts.append('<span class="badge badge-low">携带者</span>')
        if affected: parts.append('<span class="badge badge-critical">可能发病</span>')
        parts.append('</div>')

        if disease:
            desc_html = f'<p>{desc}</p>' if desc else ''
            parts.append(f'<div class="info-panel" style="--panel-color:{accent_color}"><h4>相关疾病</h4><p><strong>{disease}</strong></p>{desc_html}</div>')

        if summary:
            parts.append(f'<div class="info-panel" style="--panel-color:#3b82f6"><h4>医学解读</h4><p>{summary}</p></div>')

        if inh.get('explanation'):
            parts.append(f'<div class="info-panel" style="--panel-color:#eab308"><h4>遗传风险评估</h4><p>{inh["explanation"]}</p></div>')

        if drugs:
            drug_parts = ['<div class="info-panel" style="--panel-color:#3b82f6"><h4>&#128138; 药物指导</h4>']
            for d in drugs:
                drug_parts.append(f'<div class="drug-card"><div class="drug-name">{d["drug"]}</div><div class="drug-effect">{d["effect"]}</div><div class="drug-action">{d["action"]}</div></div>')
            drug_parts.append('</div>')
            parts.extend(drug_parts)

        if actions:
            li = ''.join(f'<li>{a}</li>' for a in actions)
            parts.append(f'<div class="info-panel" style="--panel-color:#10b981"><h4>&#10003; 建议行动</h4><ul>{li}</ul></div>')

        if surveillance:
            li = ''.join(f'<li>{s}</li>' for s in surveillance)
            parts.append(f'<div class="info-panel" style="--panel-color:#f97316"><h4>&#128203; 监测建议</h4><ul>{li}</ul></div>')

        if lifestyle:
            li = ''.join(f'<li>{l}</li>' for l in lifestyle)
            parts.append(f'<div class="info-panel" style="--panel-color:#10b981"><h4>&#127807; 生活方式</h4><ul>{li}</ul></div>')

        if has_personal:
            parts.append(ReportEngine._render_personal(personal))

        parts.append('</div>')
        return ''.join(parts)

    @staticmethod
    def _render_personal(ctx):
        if not ctx: return ''
        lines = []
        if ctx.get('personalized_risk'):
            lines.append(f'<p>&#128202; <strong>风险评估：</strong>{ctx["personalized_risk"]}</p>')
        if ctx.get('relevant_medications'):
            meds = '、'.join(ctx['relevant_medications'])
            lines.append(f'<p>&#128138; <strong>相关用药：</strong>{meds}</p>')
        if ctx.get('relevant_family'):
            fh = '、'.join([f"{f['relation']}有{f['condition']}" for f in ctx['relevant_family']])
            lines.append(f'<p>&#128106; <strong>家族史：</strong>{fh}</p>')
        if ctx.get('lifestyle_factors'):
            lf = '、'.join(ctx['lifestyle_factors'])
            lines.append(f'<p>&#127807; <strong>生活方式：</strong>{lf}</p>')
        if ctx.get('personalized_advice'):
            for a in ctx['personalized_advice']:
                lines.append(f'<p>&#128161; {a}</p>')
        return f'<div class="personal-context"><h4>&#128100; 基于您的个人档案</h4>{"".join(lines)}</div>'

    @staticmethod
    def _render_footer():
        return '<div class="report-footer"><div class="version">DNA Personal Genome Intelligence v0.4</div>'
        + '<p>本报告基于公开医学数据库和遗传学知识生成，仅供教育和研究参考。</p>'
        + '<p>不能替代专业遗传咨询、基因咨询师或医生的诊断和建议。</p>'
        + '<p>如有疑问，请咨询合格的医疗专业人员。</p>'
        + '<p style="margin-top:1rem;color:#475569">Generated by DNA-PGI Engine</p></div></div>'