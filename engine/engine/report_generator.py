import json
from datetime import datetime

class ReportGenerator:
    """Generate HTML and JSON reports from analyzed variants."""

    @staticmethod
    def generate_json(results, output_path):
        """Save structured JSON report."""
        report = {
            'generated_at': datetime.now().isoformat(),
            'total_variants': results.get('total', 0),
            'filtered_variants': len(results.get('variants', [])),
            'findings': results.get('variants', []),
        }

        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)

        return report

    @staticmethod
    def generate_html(results, output_path):
        """Generate a human-readable HTML report."""
        variants = results.get('variants', [])
        total = results.get('total', 0)

        # Categorize
        critical = [v for v in variants if v.get('priority') == 'CRITICAL']
        high = [v for v in variants if v.get('priority') == 'HIGH']
        moderate = [v for v in variants if v.get('priority') == 'MODERATE']
        low = [v for v in variants if v.get('priority') == 'LOW']

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Personal Genome Report</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; max-width: 800px; margin: 0 auto; padding: 2rem; background: #f8fafc; color: #1e293b; }}
        .header {{ text-align: center; margin-bottom: 2rem; }}
        .header h1 {{ font-size: 2rem; margin-bottom: 0.5rem; }}
        .header p {{ color: #64748b; }}
        .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 1rem; margin-bottom: 2rem; }}
        .stat {{ background: white; padding: 1rem; border-radius: 8px; text-align: center; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
        .stat .num {{ font-size: 1.5rem; font-weight: 700; }}
        .stat .label {{ font-size: 0.75rem; color: #94a3b8; text-transform: uppercase; }}
        .section {{ background: white; border-radius: 12px; padding: 1.5rem; margin-bottom: 1.5rem; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
        .section-title {{ font-size: 1.1rem; font-weight: 700; margin-bottom: 1rem; display: flex; align-items: center; gap: 0.5rem; }}
        .variant {{ border-left: 4px solid #e2e8f0; padding: 1rem; margin-bottom: 0.75rem; background: #f8fafc; border-radius: 0 8px 8px 0; }}
        .variant.critical {{ border-left-color: #dc2626; background: #fef2f2; }}
        .variant.high {{ border-left-color: #ea580c; background: #fff7ed; }}
        .variant.moderate {{ border-left-color: #d97706; background: #fffbeb; }}
        .variant.low {{ border-left-color: #16a34a; background: #f0fdf4; }}
        .gene {{ font-weight: 700; font-size: 1.05rem; }}
        .meta {{ color: #64748b; font-size: 0.9rem; margin: 0.25rem 0; }}
        .badge {{ display: inline-block; padding: 0.2rem 0.6rem; border-radius: 999px; font-size: 0.75rem; font-weight: 600; margin-right: 0.5rem; }}
        .badge-red {{ background: #fee2e2; color: #dc2626; }}
        .badge-orange {{ background: #ffedd5; color: #c2410c; }}
        .badge-yellow {{ background: #fef3c7; color: #b45309; }}
        .badge-green {{ background: #d1fae5; color: #059669; }}
        .recommendations {{ margin-top: 0.75rem; padding: 0.75rem; background: white; border-radius: 6px; font-size: 0.9rem; }}
        .recommendations ul {{ margin: 0.25rem 0 0 1.2rem; padding: 0; }}
        .recommendations li {{ margin-bottom: 0.25rem; color: #475569; }}
        .empty {{ text-align: center; color: #94a3b8; padding: 1rem; font-style: italic; }}
        .footer {{ text-align: center; margin-top: 2rem; padding-top: 2rem; border-top: 1px solid #e2e8f0; color: #94a3b8; font-size: 0.8rem; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🧬 Personal Genome Report</h1>
        <p>Generated on {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
        <p>{total:,} variants analyzed · {len(variants)} findings reported</p>
    </div>

    <div class="stats">
        <div class="stat"><div class="num" style="color:#dc2626">{len(critical)}</div><div class="label">Critical</div></div>
        <div class="stat"><div class="num" style="color:#ea580c">{len(high)}</div><div class="label">High</div></div>
        <div class="stat"><div class="num" style="color:#d97706">{len(moderate)}</div><div class="label">Moderate</div></div>
        <div class="stat"><div class="num" style="color:#16a34a">{len(low)}</div><div class="label">Low</div></div>
    </div>
"""

        # Critical section
        html += ReportGenerator._render_section('🔴 Critical Findings', critical, 'critical', 'badge-red')
        html += ReportGenerator._render_section('🟠 High Priority', high, 'high', 'badge-orange')
        html += ReportGenerator._render_section('🟡 Moderate Findings', moderate, 'moderate', 'badge-yellow')
        html += ReportGenerator._render_section('🟢 Low Priority / Informational', low, 'low', 'badge-green')

        html += '''
    <div class="footer">
        <p><strong>Disclaimer:</strong> This report is for educational and research purposes only.</p>
        <p>It is not a substitute for professional genetic counseling or medical advice.</p>
        <p>Always consult a qualified healthcare provider for clinical interpretation.</p>
    </div>
</body>
</html>'''

        with open(output_path, 'w') as f:
            f.write(html)

        return html

    @staticmethod
    def _render_section(title, variants, css_class, badge_class):
        if not variants:
            return f'''
    <div class="section">
        <div class="section-title">{title}</div>
        <div class="empty">No variants in this category.</div>
    </div>'''

        cards = []
        for v in variants:
            gene = v.get('gene_name', 'Unknown')
            hgvs = v.get('hgvs_p') or v.get('hgvs_c', '')
            sig = v.get('clinvar_significance', '').replace('_', ' ').title()
            disease = v.get('disease', '')
            impact = v.get('impact', '')
            score = v.get('score', 0)
            summary = v.get('summary', '')
            recs = v.get('recommendations', [])

            rec_html = ''
            if recs:
                rec_items = ''.join(f'<li>{r}</li>' for r in recs)
                rec_html = f'<div class="recommendations"><strong>Recommendations:</strong><ul>{rec_items}</ul></div>'

            cards.append(f'''
        <div class="variant {css_class}">
            <div class="gene">{gene} <span style="font-weight:400;color:#64748b">{hgvs}</span></div>
            <div class="meta">Chr{v.get('chrom', '')}:{v.get('pos', '')} | {v.get('ref', '')}&gt;{v.get('alt', '')}</div>
            <div style="margin-bottom:0.5rem">
                <span class="badge {badge_class}">{sig}</span>
                <span class="badge badge-yellow">Impact: {impact}</span>
                <span class="badge" style="background:#f1f5f9;color:#475569">Score: {score}</span>
            </div>
            {f'<div style="color:#475569;margin-bottom:0.5rem"><strong>Disease:</strong> {disease}</div>' if disease else ''}
            {f'<div style="color:#64748b;font-size:0.9rem;margin-bottom:0.5rem">{summary}</div>' if summary else ''}
            {rec_html}
        </div>''')

        return f'''
    <div class="section">
        <div class="section-title">{title} ({len(variants)})</div>
        {''.join(cards)}
    </div>'''
